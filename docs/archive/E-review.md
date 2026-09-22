# specctl — Review & Implementation Priority

**Đối tượng review:** `D-implementation-spec.md` v2.0
**Mục đích:** Giải thích requirement nào thực sự cần, cần vì sao, và nên làm theo thứ tự nào. Tài liệu này không xếp lịch; thứ tự chỉ dựa trên phụ thuộc kỹ thuật và rủi ro.

---

## 1. Hệ thống này để làm gì

`specctl` làm đúng hai việc:

1. **Đọc hiểu spec:** agent trả lời câu hỏi về spec, mỗi câu trả lời có trích dẫn ID.
2. **Cải thiện spec:** agent sửa spec, và mọi thay đổi đều được phát hiện, được review và được giải thích.

Mọi requirement trong spec D đều nhằm chặn một trong bốn rủi ro dưới đây. Requirement nào không chặn được rủi ro nào thì có thể cắt.

| Rủi ro | Mô tả | Hậu quả nếu xảy ra |
|---|---|---|
| **R1 — Mất nội dung khi chuyển đổi** | Parser .docx âm thầm bỏ sót đoạn văn, bảng, text box, hoặc đưa text đã bị xoá (tracked deletion) vào vault | Vault không còn đúng với spec gốc. Mọi thứ xây trên nó đều sai, mà không ai biết |
| **R2 — Không có địa chỉ ổn định** | Nội dung chỉ được định vị bằng số dòng hoặc số mục, là những thứ thay đổi mỗi lần sửa | Không trích dẫn được, không theo dõi được thay đổi, không có khoá dòng cho Excel |
| **R3 — AI âm thầm đổi nội dung** | Agent đổi `50 ms` thành `80 ms`, xoá một câu, hoặc sửa một hình | Spec hợp đồng bị sai, và không ai phát hiện |
| **R4 — Không chứng minh được thay đổi** | Không trả lời được câu "cái gì đã đổi, so với bản nào, vì sao" | Không giao được cho customer, không audit được |

---

## 2. Requirement theo mức độ cần thiết

### Tầng 1 — Bắt buộc (không có thì hệ thống vô nghĩa)

| Feature | Spec D | Chặn rủi ro | Vì sao cần |
|---|---|---|---|
| **Block ID ổn định** — mỗi block có ID bất biến, không tái sử dụng | §5.1–5.3 | R2 | Là nền tảng của mọi thứ khác: trích dẫn, diff, backlinks, dòng Excel. Không có ID thì không có hệ thống |
| **Định dạng section file** — anchor `<!-- id:… -->`, front matter, mỗi section một file | §6.1–6.3 | R2 | Là "hợp đồng" chung mà mọi command cùng đọc và ghi. Nếu nó mơ hồ, mỗi command sẽ hiểu một kiểu |
| **Hàm text dùng chung** — `normalize`, `to_plain_text`, `words` | §6.6 | R1, R3 | Bốn nơi (fidelity, registry, numeric diff, Excel) phải so sánh text theo cùng một cách. Nếu mỗi nơi tự viết, kết quả sẽ mâu thuẫn nhau |
| **Ingest: walker đầy đủ** — descend `w:sdt`, bỏ `w:del`, giữ `w:ins`, bỏ TOC/header/footer có ghi nhận | §10.5 | R1 | Đây là nơi dễ mất dữ liệu âm thầm nhất. Nếu chỉ gom `w:t`, text đã bị xoá sẽ xuất hiện như requirement thật |
| **Nguyên tắc total-capture** — thứ gì không biểu diễn được thì degrade thành block `raw` bị khoá, không bao giờ bỏ | §6.4 | R1 | Đảm bảo "không biểu diễn được" không bao giờ thành "biến mất" |
| **Bảng: pipe / HTML / degrade** | §10.6 | R1 | Spec automotive chứa nhiều bảng có merge cell. Ép bảng phức tạp thành pipe table sẽ làm mất cấu trúc |
| **Đo fidelity theo một chiều** — bao nhiêu % text nguồn tìm thấy trong vault | §10.12 | R1 | Là bằng chứng duy nhất cho thấy vault đáng tin. Dùng tỉ lệ ròng thì phần mất và phần thêm triệt tiêu nhau, che giấu phần bị mất |
| **Coverage report + gates** | §8, §10.1 | R1 | Biến "chắc là đủ" thành con số đo được, kèm danh sách từng chỗ bị thiếu |
| **Numbering heading/list từ `numbering.xml`** | §10.3 | R2 | Số mục như "3.2" không nằm trong text của Word. Không tính lại thì mất cấu trúc tài liệu |
| **Deterministic, no network** | §9.5 | R1, R3 | Chạy lại phải ra đúng kết quả cũ. Không có network thì chứng minh được bằng test rằng không có LLM nào nằm trong đường chuyển đổi |

### Tầng 2 — Cần cho Problem A (đọc hiểu)

| Feature | Spec D | Vì sao cần |
|---|---|---|
| **Cross-ref → wikilink** — đọc bookmark/REF từ OOXML | §6.5, §10.4 | Tham chiếu chéo là cách spec tự nối các phần với nhau. Converter thông thường làm mất chúng, và khi đó agent không đi theo được "xem mục 5.1" |
| **`index.md`** | §13.2 | Là bản đồ của agent: đọc một file nhỏ để biết cần mở section nào, thay vì đọc cả vault |
| **`CLAUDE.md` + 3 skill đọc** — navigate, understand, answer-with-citations | §14, §15 | Nếu không quy định rõ, agent sẽ trả lời mà không trích dẫn ID, tức là không kiểm chứng được |
| **Section front matter** (không có preamble) | §10.9 | Revision history nằm trước heading đầu tiên và là nội dung hợp đồng. Không có section riêng thì nó không có chỗ nằm |

### Tầng 3 — Cần cho Problem B (cải thiện)

| Feature | Spec D | Chặn rủi ro | Vì sao cần |
|---|---|---|---|
| **`validate` — V10 numeric/unit diff** | §12.6 | R3 | **Tuyến phòng thủ chính** chống việc agent đổi giá trị. So sánh theo multiset nên đảo thứ tự câu không báo nhầm, còn đổi số thì luôn bị bắt |
| **`validate` — V05 locked block** | FMT-08 | R3 | Hình, shape và fallback không review được bằng text diff, nên phải khoá cứng |
| **`validate` — V04 xoá block + lineage** | §5.4, §12.5 | R3, R4 | Phân biệt "bị xoá" với "đã gộp vào block khác". Không có lineage thì mọi thao tác restructure trông như xoá nội dung, cả với validator lẫn với customer |
| **`validate` — V01–V03, V07** | §12.3 | R2 | ID trùng, anchor hỏng hoặc link chết làm vỡ toàn bộ hệ địa chỉ |
| **Base = merge-base** | §12.2 | R3 | Nếu mặc định so với `HEAD` thì sau khi commit trên branch, validator so với chính bản đã sửa và báo "sạch" sai |
| **`fmt`** — tính lại front matter dẫn xuất | §11 | R2 | Agent điều hướng bằng `breadcrumb`. Nếu để sửa tay, nó sẽ lệch và agent đi sai mà không có cảnh báo nào |
| **`--assign-ids`** (chỉ cho block) | §12.4 | R2 | Block mới do agent viết cần có ID trước khi commit |
| **Edit workflow + quy tắc commit** | §16, §17 | R3, R4 | Agent không được commit. Người review diff là chốt chặn cuối |
| **Skill restructure/rewrite** | §15 | — | Là mục đích của Problem B. Phụ thuộc [OWNER-2] (target structure) |
| **`export xlsx`** với cột Change | §13.5–13.6 | R4 | Là deliverable cho customer: thay đổi được phân loại theo ID và lineage, không theo vị trí |
| **`log.md`** | §13.4 | R4 | Nguồn duy nhất cho cột Rationale trong Excel |

### Tầng 4 — Nên có, nhưng hệ thống vẫn chạy nếu thiếu

| Feature | Spec D | Vì sao hoãn được |
|---|---|---|
| Render shape qua LibreOffice | §10.7 | Đã có đường degrade sang `raw` + OOXML, nên không mất dữ liệu, chỉ thiếu hình minh hoạ |
| OMML → LaTeX | §10.8 | Có fallback bằng hình. Ngoài ra còn rủi ro license khi vendor `OMML2MML.XSL` |
| `backlinks.md` | §13.3 | Dùng `rg` theo ID cũng thay được |
| V06, V08, V09, V11–V17 | §12.3 | Phần lớn đã được `fmt` tự sửa, hoặc chỉ ở mức info/warn |
| Pre-commit hook | §20 | Thêm một lớp an toàn, nhưng workflow thủ công vẫn đủ |
| Golden set / eval | §19 ACC-8 | Dùng để đo chất lượng, không cần để hệ thống chạy |

### Tầng 5 — Có thể cắt hoặc hoãn

| Feature | Spec D | Lý do |
|---|---|---|
| **Re-ingest matching** | §10.10 | Chỉ cần khi customer gửi bản .docx mới. Hiện spec **chưa giải quyết** việc re-ingest sẽ ghi đè các edit đã làm (xem mục 3). Nên hoãn đến khi có luồng hợp nhất |
| `--assign-ids` tạo section mới | §5.5 | Hiếm dùng, lại mâu thuẫn quy tắc một file mỗi session. Có thể làm tay |
| `textual_ref_candidate`, `style_dropped` | App. B | Chỉ để quan sát |
| Performance budget | §9.5 | Với một file khoảng 1200 block thì hầu như chắc chắn đạt mà không cần tối ưu |

---

## 3. Lỗi trong spec D cần sửa trước khi code

### Nghiêm trọng

1. **Split tạo ra trạng thái mâu thuẫn** (§5.4 L3, §12.5, App. D).
   - L3 vừa nói "MUST carry `split_from`" vừa nói "MAY omit".
   - Trong ví dụ, ID gốc vẫn còn trong vault nhưng bị ghi `split`, là trạng thái terminal.
   - **Sửa:** mọi phần sau khi split đều nhận ID mới, còn ID gốc biến mất khỏi vault.

2. **V04b báo lỗi sai cho mọi lần split** (§12.5).
   - Pseudocode "claimed more than once" áp dụng cho cả `split_from`. Nhưng split thành N phần thì hiển nhiên có N block claim cùng một ID.
   - **Sửa:** chỉ áp dụng V04b cho `supersedes`.

3. **`validate` ghi vào `meta/ids.json`** (§12.4, §12.5).
   - Validator có side-effect nên chạy lại không cho cùng kết quả, trong khi nó được gọi nhiều lần và cả trong hook.
   - **Sửa:** `validate` chỉ đọc. Việc cập nhật registry tách thành bước riêng, chạy sau commit.

4. **Thứ tự các bước trong edit workflow không chạy được** (§16).
   - Hook `index --check` chạy trước khi `index` được sinh lại.
   - `log` cần SHA nên luôn tạo ra file chưa commit.
   - Squash merge làm mất SHA, khiến cột Rationale trong Excel trống.
   - **Sửa:** chạy `index` trước commit, ghi `log` trong một commit riêng, và cấm squash merge.

### Quan trọng

5. **Re-ingest ghi đè edit** (§10.10). Sau khi vault đã là source of truth thì re-ingest từ .docx sẽ xoá công sức của Problem B. Ngoài ra, vì match chỉ trong từng section nên con số "block đổi section" của M5 luôn bằng 0.
6. **Section mới không có giá trị hợp lệ cho `source` và `bookmarks`**, dù cả hai đều required và immutable (§6.2, App. A.1).
7. **`--assign-ids` tự mâu thuẫn**: vừa yêu cầu "every other byte unchanged", vừa phải chuyển nội dung sang file mới (§12.4 so với §5.5).
8. **[OWNER-3] chưa phải điều kiện chặn.** Chưa có ý kiến của customer về việc đưa nội dung spec lên cloud model thì không được mở session agent nào trên nội dung thật.

### Nhỏ

9. **Fidelity:**
   - Segment ngắn ("Yes", "1") khớp ở bất kỳ đâu, làm coverage bị thổi phồng.
   - `candidate_sections()` chưa được định nghĩa.
   - `to_plain_text` phải bỏ escape Markdown (`\|`, `\*`).
10. **Numeric grammar:**
    - Thiếu word boundary, nên chữ số trong tên signal (`Sig2`, `0x1F`) cũng bị bắt thành số.
    - `1,5` bị hiểu thành `15`.

---

## 4. Thứ tự implement

Thứ tự dựa trên phụ thuộc: mỗi bước chỉ dùng những gì các bước trước đã tạo ra.

| # | Feature | Phụ thuộc | Ghi chú |
|---|---|---|---|
| 1 | **Thử fidelity trên file thật** — walker tối giản + đo coverage | — | Kiểm tra xem Markdown có đủ làm store không. Nếu không đạt thì dừng lại xem lại DEC-01 trước khi làm gì khác. Cần [OWNER-1] |
| 2 | **Core lib** — model, textutil, parser/serializer anchor và front matter, config, schemas | — | Mọi command đều dùng. Viết sai ở đây thì sai lan ra toàn bộ |
| 3 | **Ingest lõi** — walker, numbering, segment, cấp ID, writer | 2 | |
| 4 | **Bảng + fidelity + coverage + gates** | 3 | Từ đây đã chứng minh được vault không mất dữ liệu |
| 5 | **Cross-ref → wikilink** | 3 | |
| 6 | **`index.md` + `CLAUDE.md` + skill đọc** | 4, 5, [OWNER-3] | Problem A dùng được từ đây |
| 7 | **`fmt`** | 2 | Phải có trước `validate` |
| 8 | **`validate` lõi** — V01–V05, V07, V10, lineage, merge-base | 7, sửa lỗi 1–3 | **Bắt buộc có trước khi agent được sửa file** |
| 9 | **`--assign-ids`** (block) | 8 | |
| 10 | **Edit workflow + skill edit** | 8, 9, [OWNER-2], sửa lỗi 4 | Problem B dùng được từ đây |
| 11 | **`log` + `export xlsx`** | 8, 10 | Có deliverable cho customer |
| 12 | Tầng 4 (shapes, equations, backlinks, rule còn lại, hook, eval) | tuỳ mục | Làm dần |
| 13 | Tầng 5 (re-ingest, …) | sửa lỗi 5 | Chỉ làm khi có nhu cầu thật |

**Nguyên tắc quan trọng nhất:** `validate` (bước 8) phải xong **trước** khi agent sửa bất kỳ section nào (bước 10). Lịch trong spec D đang làm ngược lại, cho agent sửa trước rồi mới có validator. Như vậy trái với DEC-08 và bỏ trống lớp phòng thủ chính chống R3.
