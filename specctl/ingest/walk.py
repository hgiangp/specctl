"""The block stream: every piece of the document, in document order (§10.5).

**This is the module where content is silently lost if it is written casually.** A reader
that collects `w:t` descendants and joins them runs cleanly, produces plausible Markdown,
and is wrong in two directions at once: it drops the paragraph wrapped in a content
control, and it emits the paragraph the author deleted as though it were a live
requirement. Neither shows up as an error. That is Failure 1, and it is why this module is
written as a recursive walk over *every* child rather than as a set of XPath queries for
the elements someone remembered.

The shape follows §10.5 exactly, and the rules keep their names:

| Rule | Here                                                                       |
| ---- | -------------------------------------------------------------------------- |
| W1   | `w:ins` is walked, `w:del` is not, and both are counted                     |
| W2   | any revision at all raises `source_has_unresolved_revisions`                |
| W3   | comment anchors are dropped, the text they annotate is kept, both counted   |
| W4   | a TOC field, and TOC-styled paragraphs, are skipped and accounted           |
| W5   | headers, footers and note separators are skipped and accounted              |
| W6   | an unrecognised element holding content is descended into, with an issue    |

What comes out is a stream of items, not Markdown. Deciding how a table is represented
(F09), what a shape degrades to (F10), which section an item lands in (F07) and what its
number is (F06) all happen later and all read this stream. Keeping those out of here is
what makes the loss question answerable on its own: if the text reached the stream, no
later stage can lose it without a named reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from lxml import etree

from ..textutil import normalize
from .package import NS, Package, qn
from .report import Counter, Issue, Revisions, Skip, sorted_issues

# --------------------------------------------------------------------------- tags

P = qn("w:p")
TBL = qn("w:tbl")
SDT = qn("w:sdt")
SDT_CONTENT = qn("w:sdtContent")
INS = qn("w:ins")
DEL = qn("w:del")
SMART_TAG = qn("w:smartTag")
CUSTOM_XML = qn("w:customXml")
ALTERNATE_CONTENT = qn("mc:AlternateContent")
CHOICE = qn("mc:Choice")
FALLBACK = qn("mc:Fallback")

T = qn("w:t")
DEL_TEXT = qn("w:delText")
INSTR_TEXT = qn("w:instrText")
DEL_INSTR_TEXT = qn("w:delInstrText")
TAB = qn("w:tab")
BR = qn("w:br")
CR = qn("w:cr")
NO_BREAK_HYPHEN = qn("w:noBreakHyphen")
SOFT_HYPHEN = qn("w:softHyphen")
SYM = qn("w:sym")

P_PR = qn("w:pPr")
R_PR = qn("w:rPr")
P_STYLE = qn("w:pStyle")
FLD_CHAR = qn("w:fldChar")
FLD_CHAR_TYPE = qn("w:fldCharType")
FLD_SIMPLE = qn("w:fldSimple")
INSTR_ATTR = qn("w:instr")
VAL = qn("w:val")
TYPE_ATTR = qn("w:type")

COMMENT_REFERENCE = qn("w:commentReference")
COMMENT_RANGE_START = qn("w:commentRangeStart")
COMMENT_RANGE_END = qn("w:commentRangeEnd")

DRAWING = qn("w:drawing")
PICT = qn("w:pict")
OBJECT = qn("w:object")
O_MATH = qn("m:oMath")
O_MATH_PARA = qn("m:oMathPara")
M_T = qn("m:t")
TXBX_CONTENT = qn("w:txbxContent")
BLIP = qn("a:blip")
IMAGEDATA = qn("v:imagedata")

FOOTNOTE = qn("w:footnote")
ENDNOTE = qn("w:endnote")

#: §10.5 — containers that are packaging, never content. Walked straight through.
#: `w:ins` and `w:sdt` are handled separately: one is counted, the other has a wrapper
#: element to step into first.
TRANSPARENT = frozenset({SMART_TAG, CUSTOM_XML})

#: Objects a paragraph *contains* rather than *is*. Their text is recovered separately so
#: that a text box counts once (§10.12 F4) and the object still reaches F10 whole.
EMBEDDED = frozenset({DRAWING, PICT, OBJECT, O_MATH, O_MATH_PARA, ALTERNATE_CONTENT})

#: Never part of a paragraph's own text. `w:instrText` is a field *instruction* — the
#: field's rendered result is a separate run and is kept.
NON_TEXT = frozenset({DEL_TEXT, INSTR_TEXT, DEL_INSTR_TEXT})

#: W5 — a note whose `w:type` is one of these is furniture Word inserts, not content.
SEPARATOR_NOTE_TYPES = frozenset({"separator", "continuationSeparator", "continuationNotice"})

#: W4 — `TOC1`…`TOC9`. `TOCHeading` is deliberately excluded: it styles the words "Table
#: of Contents" itself, which is an ordinary heading the document really contains.
TOC_STYLE = re.compile(r"^TOC\s*\d+$", re.IGNORECASE)

#: Parts are walked in this order, and the paragraph index runs across all of them, so
#: every issue and every item has one comparable address (§8.4 sorts by it).
PART_ORDER: tuple[str, ...] = ("document", "footnotes", "endnotes")


# --------------------------------------------------------------------------- results

@dataclass(frozen=True, eq=False)
class Embedded:
    """A drawn or embedded object found inside a paragraph.

    Carried with its element so F10 can write the verbatim OOXML beside the block, and
    with whatever text is recoverable from inside it so that a text box holding a
    requirement is searchable rather than merely rendered (§10.7).
    """

    kind: str          # "image" | "textbox" | "shape" | "object" | "formula"
    tag: str
    paragraph: int
    text: str
    element: etree._Element


@dataclass(frozen=True, eq=False)
class StreamItem:
    """One `w:p` or `w:tbl`, in document order, with its text already recovered.

    `text` is the accepted-revision state: insertions in, deletions out, field
    instructions out, embedded objects out (they are in `embedded`). Nothing here is
    normalized — `textutil.normalize` is applied by whoever compares, so that the raw
    spacing is still available to the writer.
    """

    kind: str          # "paragraph" | "table"
    paragraph: int
    part: str
    element: etree._Element
    text: str
    embedded: tuple[Embedded, ...] = ()
    cell_texts: tuple[str, ...] = ()

    @property
    def is_table(self) -> bool:
        return self.kind == "table"

    def texts(self) -> tuple[str, ...]:
        """Every distinct string this item contributes — its own, then its objects'.

        A text box appears here once, not twice: §10.12 F4 says text emitted twice
        counts once, and the place to make that true is where the text is produced.
        """
        out = [self.text] if self.text else []
        out += [e.text for e in self.embedded if e.text]
        return tuple(out)


@dataclass(frozen=True)
class BlockStream:
    """Everything the walk observed: what was kept, what was dropped, and why."""

    items: tuple[StreamItem, ...]
    revisions: Revisions
    skipped: dict[str, Skip]
    issues: tuple[Issue, ...]

    def texts(self) -> tuple[str, ...]:
        return tuple(t for item in self.items for t in item.texts())

    def of_kind(self, kind: str) -> tuple[StreamItem, ...]:
        return tuple(i for i in self.items if i.kind == kind)

    def embedded(self) -> tuple[Embedded, ...]:
        return tuple(e for i in self.items for e in i.embedded)

    def issues_with(self, code: str) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.code == code)


# --------------------------------------------------------------------------- field state

@dataclass
class _Field:
    """One open Word field. Fields nest, and a field's instruction can be split across
    several `w:instrText` runs, so the instruction is accumulated rather than read once."""

    instruction: str = ""

    @property
    def is_toc(self) -> bool:
        return self.instruction.strip().upper().startswith("TOC")


# --------------------------------------------------------------------------- the walker

class _Walker:
    def __init__(self, package: Package) -> None:
        self.package = package
        self.counter = Counter()
        self.items: list[StreamItem] = []
        self.fields: list[_Field] = []
        self.first_revision_paragraph: int | None = None
        self._index: dict[int, int] = {}
        # lxml hands out a fresh proxy object each time an element is reached and frees it
        # when the last reference goes. `id()` of a freed proxy can be reused by the next
        # one, which would silently corrupt this map — so every indexed element is kept
        # alive for the lifetime of the walk.
        self._alive: list[etree._Element] = []

    # -- addressing ---------------------------------------------------------

    def _build_index(self, roots: Sequence[etree._Element]) -> None:
        """Number every paragraph in document order, across the parts, once.

        A table is not a paragraph, so it takes the index its first inner paragraph will
        get: `iter()` reaches `w:tbl` before the cells inside it, which makes "paragraphs
        seen so far" exactly that number, with no special case.
        """
        n = 0
        for root in roots:
            for element in root.iter():
                if element.tag == P:
                    self._index[id(element)] = n
                    self._alive.append(element)
                    n += 1
                elif element.tag == TBL:
                    self._index[id(element)] = n
                    self._alive.append(element)

    def index_of(self, element: etree._Element) -> int:
        return self._index.get(id(element), -1)

    # -- W4: field tracking -------------------------------------------------

    @property
    def in_toc(self) -> bool:
        return any(f.is_toc for f in self.fields)

    def _scan_fields(self, element: etree._Element) -> bool:
        """Advance the field state over one paragraph; report whether a TOC was open
        at any moment inside it.

        A TOC field opens in one paragraph and closes several paragraphs later, so the
        state has to survive between items. Checking only the paragraph in hand would
        keep every entry of the table of contents as a requirement.
        """
        touched_toc = self.in_toc
        for node in element.iter():
            tag = node.tag
            if tag == FLD_CHAR:
                kind = node.get(FLD_CHAR_TYPE)
                if kind == "begin":
                    self.fields.append(_Field())
                elif kind == "end" and self.fields:
                    self.fields.pop()
            elif tag in (INSTR_TEXT, DEL_INSTR_TEXT):
                if self.fields:
                    self.fields[-1].instruction += node.text or ""
            elif tag == FLD_SIMPLE:
                if (node.get(INSTR_ATTR) or "").strip().upper().startswith("TOC"):
                    touched_toc = True
            touched_toc = touched_toc or self.in_toc
        return touched_toc

    @staticmethod
    def _toc_styled(element: etree._Element) -> bool:
        style = element.find(f"{P_PR}/{P_STYLE}")
        return style is not None and bool(TOC_STYLE.match(style.get(VAL) or ""))

    # -- the recursion ------------------------------------------------------

    def walk(self, node: etree._Element, part: str) -> None:
        for child in node:
            tag = child.tag
            if not isinstance(tag, str):
                continue  # a comment or processing instruction carries no content

            if tag in (P, TBL):
                self._consider(child, part)

            elif tag == SDT:                              # content control — packaging
                content = child.find(SDT_CONTENT)
                if content is not None:
                    self.walk(content, part)
                elif self._holds_content(child):
                    # An sdt with content but no sdtContent is malformed; descending is
                    # still the right answer, because the alternative is losing it.
                    self.counter.issue(
                        "unknown_container", self._nearby_index(child), "w:sdt/@no-sdtContent"
                    )
                    self.walk(child, part)

            elif tag == ALTERNATE_CONTENT:
                chosen = child.find(CHOICE)
                if chosen is None:
                    chosen = child.find(FALLBACK)
                if chosen is not None:
                    self.walk(chosen, part)

            elif tag == INS:                              # W1 — accepted, current content
                self._count_revision("ins", self._nearby_index(child))
                self.walk(child, part)

            elif tag == DEL:                              # W1 — discarded, never walked
                self._count_revision("del", self._nearby_index(child))

            elif tag in TRANSPARENT:
                self.walk(child, part)

            elif tag in EMBEDDED:
                # A drawing or an OLE object standing where a paragraph would. Its
                # insides belong to the object: descending would emit a text box's
                # paragraphs as page content and count that text twice (§10.12 F4).
                self._leaf(child, part)

            elif self._holds_content(child):              # W6 — never dropped
                self.counter.issue("unknown_container", self._nearby_index(child), _name(tag))
                self.walk(child, part)

            else:
                self._leaf(child, part)

    @staticmethod
    def _holds_content(element: etree._Element) -> bool:
        for descendant in element.iterdescendants():
            if descendant.tag in (P, TBL):
                return True
        return False

    def _leaf(self, element: etree._Element, part: str) -> None:
        """An element with no paragraph or table inside it.

        Almost always `w:sectPr`, `w:bookmarkStart` or another marker with nothing to
        capture. When it does carry text, though, dropping it silently is the failure
        this module exists to prevent — so it is emitted as a paragraph-shaped item and
        reported, which puts an odd construct in front of a reviewer instead of in a
        diff nobody will ever see.
        """
        if element.tag in EMBEDDED:
            # This element *is* the object, so it is described directly —
            # `_embedded_of` searches inside an element and would find nothing here.
            # Emitted whether or not anything is readable inside it: an image has no text
            # by nature, so gating on text would drop every figure standing at body
            # level. "Nothing to read" is not the same fact as "nothing there", and F10
            # cannot degrade an object that never reached the stream.
            index = self._nearby_index(element)
            self.items.append(
                StreamItem(kind="paragraph", paragraph=index, part=part,
                           element=element, text="",
                           embedded=(self._describe(element, index),))
            )
            return

        text = self._text_of(element)
        if not normalize(text):
            return
        index = self._nearby_index(element)
        self.counter.issue("unknown_container", index, _name(element.tag))
        self.items.append(
            StreamItem(kind="paragraph", paragraph=index, part=part,
                       element=element, text=text)
        )

    def _nearby_index(self, element: etree._Element) -> int:
        """The paragraph index to file something against that is not itself a paragraph.

        The first indexed node at or below it, else the nearest indexed ancestor. Every
        issue must be addressable (§10.12 F5); an issue at paragraph -1 is a complaint
        with no location.
        """
        own = self._index.get(id(element))
        if own is not None:
            return own
        for descendant in element.iterdescendants():
            found = self._index.get(id(descendant))
            if found is not None:
                return found
        for ancestor in element.iterancestors():
            found = self._index.get(id(ancestor))
            if found is not None:
                return found
        return max((i.paragraph for i in self.items), default=0)

    # -- emitting -----------------------------------------------------------

    def _consider(self, element: etree._Element, part: str) -> None:
        """Decide whether this paragraph or table is content, then emit or account it."""
        paragraphs = [element] if element.tag == P else list(element.iter(P))
        in_toc_before = self.in_toc
        touched_toc = False
        for paragraph in paragraphs:
            touched_toc = self._scan_fields(paragraph) or touched_toc
        styled_toc = element.tag == P and self._toc_styled(element)

        if in_toc_before or touched_toc or styled_toc:
            self._account("toc", paragraphs)
            return

        self._emit(element, part)

    def _emit(self, element: etree._Element, part: str) -> None:
        index = self.index_of(element)
        self._count_inline_revisions(element, index)

        if element.tag == P:
            item = StreamItem(
                kind="paragraph", paragraph=index, part=part, element=element,
                text=self._text_of(element),
                embedded=self._embedded_of(element, index),
            )
        else:
            cells = tuple(self._text_of(cell) for cell in element.iter(qn("w:tc")))
            item = StreamItem(
                kind="table", paragraph=index, part=part, element=element,
                text="\n".join(t for t in cells if t),
                embedded=self._embedded_of(element, index),
                cell_texts=cells,
            )
        self.items.append(item)

    def _account(self, code: str, paragraphs: Iterable[etree._Element]) -> None:
        """Record a deliberate skip in paragraphs and characters (§8.3)."""
        paragraphs = list(paragraphs)
        chars = sum(len(normalize(self._text_of(p))) for p in paragraphs)
        self.counter.skip(code, paragraphs=len(paragraphs), chars=chars)

    # -- text recovery ------------------------------------------------------

    def _text_of(self, element: etree._Element) -> str:
        parts: list[str] = []
        self._collect_text(element, parts)
        return "".join(parts)

    def _collect_text(self, node: etree._Element, out: list[str]) -> None:
        """The accepted-revision text of a subtree.

        Written as a descent rather than `iter()` so that `w:del` prunes the whole
        subtree below it. Testing each node for a deleted ancestor instead would be the
        same answer computed more expensively — and one missed check away from emitting
        deleted text as a requirement.
        """
        for child in node:
            tag = child.tag
            if not isinstance(tag, str):
                continue
            if tag == DEL or tag in NON_TEXT or tag in EMBEDDED:
                continue
            if tag == T:
                out.append(child.text or "")
            elif tag == TAB:
                out.append("\t")
            elif tag in (BR, CR):
                out.append("\n")
            elif tag == NO_BREAK_HYPHEN:
                out.append("‑")
            elif tag == SOFT_HYPHEN:
                out.append("­")
            elif tag == SYM:
                out.append(_symbol_char(child))
            elif tag in (COMMENT_REFERENCE, COMMENT_RANGE_START, COMMENT_RANGE_END):
                continue                                   # W3 — the anchor, not the text
            else:
                self._collect_text(child, out)

    def _math_text(self, node: etree._Element) -> str:
        return "".join(t.text or "" for t in node.iter(M_T))

    # -- embedded objects ---------------------------------------------------

    def _embedded_of(self, element: etree._Element, index: int) -> tuple[Embedded, ...]:
        found: list[etree._Element] = []
        self._find_embedded(element, found)
        return tuple(self._describe(node, index) for node in found)

    def _find_embedded(self, node: etree._Element, out: list[etree._Element]) -> None:
        for child in node:
            tag = child.tag
            if not isinstance(tag, str) or tag == DEL:
                continue
            if tag in EMBEDDED:
                out.append(child)
                continue          # an object's insides belong to the object, not the page
            self._find_embedded(child, out)

    def _describe(self, node: etree._Element, index: int) -> Embedded:
        """Classify an embedded object and recover whatever text is inside it."""
        target = node
        if node.tag == ALTERNATE_CONTENT:
            # Exactly one branch, or the text box inside it is counted twice (§10.12 F4).
            chosen = node.find(CHOICE)
            if chosen is None:
                chosen = node.find(FALLBACK)
            if chosen is not None:
                target = chosen

        if node.tag in (O_MATH, O_MATH_PARA):
            return Embedded("formula", _name(node.tag), index, self._math_text(node), node)

        boxes = list(target.iter(TXBX_CONTENT))
        if boxes:
            text = "\n".join(
                t for box in boxes
                for t in (self._text_of(p) for p in box.iter(P))
                if t
            )
            return Embedded("textbox", _name(node.tag), index, text, node)

        if node.tag == OBJECT:
            return Embedded("object", _name(node.tag), index, self._text_of(target), node)

        if next(target.iter(BLIP), None) is not None or next(target.iter(IMAGEDATA), None) is not None:
            return Embedded("image", _name(node.tag), index, "", node)

        return Embedded("shape", _name(node.tag), index, self._text_of(target), node)

    # -- W1/W3 counting -----------------------------------------------------

    def _count_revision(self, kind: str, index: int) -> None:
        if kind == "ins":
            self.counter.ins_accepted += 1
        else:
            self.counter.del_discarded += 1
        if self.first_revision_paragraph is None:
            self.first_revision_paragraph = index

    def _count_inline_revisions(self, node: etree._Element, index: int) -> None:
        """Run-level revisions and comment anchors inside something being emitted.

        Word records an inserted or deleted **paragraph** twice: once around the runs, and
        once on the paragraph mark, as a `w:ins`/`w:del` inside `w:pPr/w:rPr`. Counting
        both would report two insertions for every paragraph a reviewer typed once, which
        makes the number in `coverage.json` useless for judging how dirty a source is. So
        the paragraph mark is counted only when nothing of its kind was found in the
        content — a paragraph split or merged with no text changed is still an unresolved
        revision, and W2 must not go quiet on it.
        """
        seen: set[str] = set()
        self._count_content_revisions(node, index, seen)
        self._count_paragraph_mark_revision(node, index, seen)

    def _count_content_revisions(
        self, node: etree._Element, index: int, seen: set[str]
    ) -> None:
        """A `w:del` inside a `w:del` is one discarded deletion, not two, so the descent
        stops there — the same pruning the text recovery does, for the same reason."""
        for child in node:
            tag = child.tag
            if not isinstance(tag, str):
                continue
            if tag == P_PR:
                continue  # the paragraph mark's own revision, handled separately
            if tag == INS:
                self._count_revision("ins", index)
                seen.add("ins")
                self._count_content_revisions(child, index, seen)
            elif tag == DEL:
                self._count_revision("del", index)
                seen.add("del")
            elif tag == COMMENT_REFERENCE:
                self.counter.comments_discarded += 1
            else:
                self._count_content_revisions(child, index, seen)

    def _count_paragraph_mark_revision(
        self, node: etree._Element, index: int, seen: set[str]
    ) -> None:
        mark = node.find(f"{P_PR}/{R_PR}")
        if mark is None:
            return
        for kind, tag in (("ins", INS), ("del", DEL)):
            if kind not in seen and mark.find(tag) is not None:
                self._count_revision(kind, index)

    # -- W5: parts that are skipped whole -----------------------------------

    def _account_part(self, name: str) -> None:
        root = self.package.xml(name)
        paragraphs = list(root.iter(P))
        self._account("header_footer", paragraphs)

    def _note_bodies(self, root: etree._Element | None, tag: str) -> Iterator[etree._Element]:
        """Real notes, with Word's separator furniture accounted and skipped (W5)."""
        if root is None:
            return
        for note in root.iter(tag):
            if (note.get(TYPE_ATTR) or "") in SEPARATOR_NOTE_TYPES:
                self._account("header_footer", list(note.iter(P)))
                continue
            yield note

    # -- entry point --------------------------------------------------------

    def run(self) -> BlockStream:
        footnotes, endnotes = self.package.footnotes, self.package.endnotes
        roots = [self.package.body]
        roots += [footnotes] if footnotes is not None else []
        roots += [endnotes] if endnotes is not None else []
        self._build_index(roots)

        self.walk(self.package.body, "document")
        for note in self._note_bodies(footnotes, FOOTNOTE):
            self.walk(note, "footnotes")
        for note in self._note_bodies(endnotes, ENDNOTE):
            self.walk(note, "endnotes")

        for name in self.package.header_names + self.package.footer_names:
            self._account_part(name)

        revisions = self.counter.revisions()
        if revisions.total > 0:                            # W2
            self.counter.issue(
                "source_has_unresolved_revisions",
                self.first_revision_paragraph or 0,
                f"{revisions.ins_accepted} insertion(s) kept, "
                f"{revisions.del_discarded} deletion(s) discarded — review the source "
                "before treating it as a baseline",
            )

        return BlockStream(
            items=tuple(self.items),
            revisions=revisions,
            skipped=dict(self.counter.skips),
            issues=sorted_issues(self.counter.issues),
        )


# --------------------------------------------------------------------------- helpers

_PREFIX_OF = {uri: prefix for prefix, uri in NS.items()}


def _name(tag: str) -> str:
    """`"{http://…}sdt"` → `"w:sdt"`, so an issue detail reads like the spec does."""
    if tag.startswith("{"):
        uri, _, local = tag[1:].partition("}")
        return f"{_PREFIX_OF.get(uri, uri)}:{local}"
    return tag


def _symbol_char(node: etree._Element) -> str:
    """`w:sym` carries a character by code point in a symbol font."""
    code = node.get(qn("w:char"))
    if not code:
        return ""
    try:
        value = int(code, 16)
    except ValueError:
        return ""
    # Symbol-font code points live in the private use area; map them back down.
    if 0xF000 <= value <= 0xF0FF:
        value -= 0xF000
    return chr(value)


# --------------------------------------------------------------------------- public API

def walk_package(package: Package) -> BlockStream:
    return _Walker(package).run()


def walk_document(path: str | Path) -> BlockStream:
    """Read a .docx and return its block stream."""
    return walk_package(Package.open(path))


def walk_text(path: str | Path) -> tuple[str, ...]:
    """Every string the walk recovered, in document order.

    The comparison surface for the pandoc oracle (`tests/test_pandoc_oracle.py`): text
    pandoc finds here and we do not is a bug in this module, caught on a fixture rather
    than on the customer's document.
    """
    return walk_document(path).texts()
