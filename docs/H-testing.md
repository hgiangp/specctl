# Chạy và kiểm chứng specctl

**Người đọc:** người chạy test trên máy mình.
**Trạng thái hiện tại:** F01–F05 xong. Bộ đọc OOXML (`specctl/ingest/`) chạy được và có test; `specctl ingest` vẫn báo "not implemented yet" vì nó còn cần F06–F11 để ghi ra vault. Đó là hành vi đúng, không phải lỗi.

---

## 1. Cài đặt

```bash
git clone <repo> && cd specctl
git checkout claude/peaceful-keller-lsws1g

python3 -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Cần **Python 3.11 trở lên** (dùng `tomllib` trong thư viện chuẩn). Kiểm tra:

```bash
python -c "import sys; print(sys.version)"
specctl --version          # -> specctl 0.1.0
```

---

## 2. Chạy toàn bộ test

```bash
pytest
```

Kết quả mong đợi **khi chưa có file .docx gõ tay trong Word của bạn**:

```
394 passed,  4 skipped     # có cài pandoc
381 passed, 17 skipped     # không cài pandoc
```

Skip ở đây là đúng và có ý nghĩa — xem chúng là gì:

```bash
pytest -rs          # in lý do của từng skip
```

| Skip | Nghĩa là |
|---|---|
| 4 skip về fixture | `constructs.docx`, `revisions.docx`, `containers.docx` chưa có trong `tests/fixtures/`. Các file `built_*.docx` đang gánh các ca đó, nên test F05 và test oracle **vẫn chạy** |
| 13 skip nữa nếu chưa cài pandoc | Pandoc không phải dependency của `specctl` — xem mục 5 |

Nếu **không có skip nào về fixture** thì ba file Word đã có mặt và mọi test đã tự chuyển sang dùng chúng. Nếu số test khác đi, hoặc có test đỏ, xem mục 7.

### Chạy từng phần

```bash
pytest tests/test_sectionfile.py -v    # vòng đọc-ghi, phần lõi nhất
pytest tests/test_textutil.py -v       # ba hàm văn bản (§6.6)
pytest tests/test_derived.py -v        # front matter dẫn xuất
pytest tests/test_fixtures.py -v       # kiểm tra file .docx của bạn
pytest tests/test_walk.py -v           # bộ đọc OOXML (§10.5 W1–W6)
pytest -k "round_trip or canonical"    # theo tên
```

### Những test đáng chú ý

| Test | Kiểm cái gì | Vì sao quan trọng |
|---|---|---|
| `test_appendix_d_round_trips_byte_for_byte` | Ví dụ mẫu trong spec đọc ra rồi ghi lại giống **từng byte** | Nếu đỏ, bộ ghi đang làm hỏng file mà file vẫn parse được |
| `test_parse_of_serialize_is_the_identity` | Vòng đọc-ghi trên hàng trăm đầu vào sinh tự động | Test đòn bẩy cao nhất của cả dự án |
| `test_a_fenced_code_block_keeps_its_internal_blank_lines` | Khối phân định bằng anchor, không bằng dòng trắng | Cắt theo dòng trắng sẽ cắt cụt nội dung mà file vẫn parse |
| `tests/test_netguard.py` | Không có kết nối mạng nào trong suốt bộ test | Chứng minh bằng máy rằng không có AI nào trong đường chuyển đổi |
| `test_a_tracked_insertion_is_emitted_and_a_tracked_deletion_is_not` | Phần chèn ra, phần xoá không ra | Bộ đọc gom `w:t` sẽ phát đoạn đã xoá như yêu cầu còn hiệu lực — nội dung sai tạo ra bằng cách **đọc sai** |
| `test_a_field_that_spans_paragraphs_closes_again_afterwards` | Trạng thái TOC đóng lại đúng chỗ | Quên pop field là bỏ im lặng toàn bộ phần còn lại của tài liệu |
| `test_an_unrecognised_container_is_descended_into_and_reported` | W6 — vẫn đi xuống, và có ghi chú | Cái chặn được construct mà chưa ai từng thấy |
| `test_assert_deterministic_catches_a_drifting_writer` | Bộ băm cây **phát hiện được** khi không tất định | Một harness luôn pass là loại test đắt nhất |

---

## 3. Thêm file .docx của bạn

> **Không còn chặn F05.** Mỗi file Word có một **file thế chỗ** sinh từ OOXML thuần đã
> commit sẵn (`built_constructs.docx`, `built_revisions.docx`, `built_containers.docx`), nên
> bảy ca khó đều đã có file chứa nó và bộ đọc có cái để chạy. Cái file thế chỗ **không**
> chứng minh được là bộ đọc chạy đúng trên OOXML mà Word thật sự ghi ra — nên ba file dưới
> đây vẫn cần, và test vẫn báo là còn thiếu mỗi lần chạy.
>
> Ba file thế chỗ sinh ra từ `tests/support/docx.py`, dùng **chung một danh sách yêu cầu**
> với ba file Word, nên chúng không thể bao phủ ít hơn. Sửa hay dựng lại:
>
> ```bash
> python scripts/build_fixtures.py            # dựng lại
> python scripts/build_fixtures.py --check    # kiểm file đã commit còn khớp builder không
> ```

Đặt vào `tests/fixtures/` đúng tên sau:

```
tests/fixtures/constructs.docx
tests/fixtures/revisions.docx
tests/fixtures/containers.docx
```

Rồi:

```bash
pytest tests/test_fixtures.py -v
```

**Test này đọc thẳng OOXML bên trong file của bạn** và báo đúng construct nào thiếu, kèm cách thêm trong Word. Ví dụ khi thiếu:

```
tests/fixtures/revisions.docx is missing 2 required construct(s), so
T-ING-11, §10.5 W1-W2 would not actually be covered:
  - a tracked deletion: With Track Changes on, delete a sentence. Do NOT accept
    the changes before saving, or the w:del disappears and the fixture stops
    testing anything.
  - deleted text inside the deletion: w:delText is a different element from w:t
```

Đây không phải nghi thức. Word **thường không lưu đúng cái bạn nghĩ**:

| Vô tình làm | Kết quả |
|---|---|
| Accept tracked changes trước khi lưu | Mất `w:del`. File mở vẫn bình thường, test không kiểm gì |
| Xoá hết chữ trong content control | Word bỏ luôn thẻ `w:sdt` khi lưu |
| Dán mục lục dạng text | Không có field code, không có gì để skip |
| Chèn ảnh bằng "link to file" | Không có phần ảnh nào trong package |

Danh sách đầy đủ từng file phải chứa gì: `tests/fixtures/README.md`.

> **Thiếu nửa bộ thì test đỏ, không skip.** Nửa bộ là trạng thái nguy hiểm nhất: suite xanh trên những gì tình cờ có mặt và âm thầm ngừng bao phủ phần còn lại.

Đặt cả ba cùng lúc. Mọi test đang dùng file thế chỗ sẽ **tự chuyển sang file Word ngay khi nó có mặt** — `require()` ưu tiên file gõ tay, không phải sửa một dòng test nào.

Khi commit file `.docx`, `.gitattributes` đã đánh dấu chúng là binary. Đừng bỏ dòng đó — `.docx` là file ZIP, nếu git chuẩn hoá line ending thì archive hỏng, và hỏng vô hình đến khi có gì mở nó.

---

## 4. Đo trên file thật

Đây là **điểm quyết định của F11**, và chạy được ngay cả khi F05 chưa có:

```bash
python scripts/spike_coverage.py source/SYS.docx
```

Nó liệt kê tài liệu chứa gì: bao nhiêu bảng, bao nhiêu bảng có merge cell, bao nhiêu text box, bao nhiêu REF field, có track changes không, có content control không. Chạy trước khi xây bất cứ thứ gì lên trên.

Con số cần nhìn:

| Nếu thấy | Nghĩa là |
|---|---|
| `text boxes` > 0 | Có nội dung mà bộ chuyển đổi thông thường làm mất hoàn toàn |
| `tracked insertions/deletions` > 0 | Tài liệu chưa sạch — cần xem lại trước khi lấy làm mốc |
| `with merged cells` cao | Đường HTML của §10.6 gánh phần lớn, không phải đường pipe |
| `REF fields` cao | Tham chiếu chéo là dữ liệu thật, F12 có giá trị cao |
| `content controls` > 0 | Bộ đọc bắt buộc phải đi xuyên `w:sdt`, nếu không là mất nguyên đoạn |

---

## 5. So sánh với pandoc

### Cài

```bash
# Debian/Ubuntu
sudo apt-get install -y pandoc
# macOS
brew install pandoc
```

Pandoc **không phải** dependency của `specctl`. Mọi test dùng nó tự skip khi không có.

### Chạy trên file thật

```bash
python scripts/spike_coverage.py source/SYS.docx --pandoc --json spike.json
```

Kết quả có dạng:

```
Cross-check: what pandoc keeps
  version          pandoc 3.1.3
  exit code        0
  coverage         0.7647   (13/17 segments)
  gate (ACC-2)     0.99 -> FAIL

  4 segment(s) pandoc dropped, first 20:
    - 'text inside a text box.'
    ...
```

### Chạy bộ test oracle

```bash
pytest tests/test_pandoc_oracle.py -v
```

Có hai loại test trong đó:

**Loại 1 — baseline đã ghi nhận** (chạy được ngay). Ghi lại chỗ pandoc mất dữ liệu, và cả chỗ pandoc làm tốt:

| Test | Ghi nhận |
|---|---|
| `test_pandoc_loses_text_box_content` | Mất nội dung text box, cả dạng VML lẫn DrawingML |
| `test_pandoc_loses_cells_of_a_table_it_cannot_represent` | Bảng hỏng: mất ô B, C, D, **exit 0, không cảnh báo** |
| `test_pandoc_drops_a_custom_list_number_prefix` | `REQ-5.` thành `5.` — mất định danh yêu cầu |
| `test_pandoc_keeps_bookmarks_and_anchored_links` | Giữ được — phần công bằng cho pandoc |
| `test_pandoc_handles_word_style_tracked_changes` | Xử lý đúng — phần công bằng cho pandoc |

**Loại 1b — pandoc làm trọng tài cho chính fixture của ta** (chạy được ngay):

| Test | Kiểm cái gì |
|---|---|
| `test_an_independent_reader_can_open_every_built_stand_in` | Ba file `built_*.docx` là OOXML thật, không phải OOXML mà chỉ parser của ta chấp nhận. `lxml` đọc được mọi XML hợp cú pháp nên nó **không** trả lời được câu này |
| `test_the_revisions_fixture_really_carries_word_style_tracked_changes` | Track changes trong fixture đúng hình dạng Word ghi. Chính test này bắt được bug bọc `w:p` trong `w:ins` — parse được, qua được kiểm tra `//w:ins`, và bị bỏ im lặng |

Nếu một test trong nhóm này **đỏ**, nghĩa là pandoc đã cải thiện. Đừng xoá test — chạy lại so sánh và đánh giá lại quyết định.

**Loại 2 — oracle thật** (`test_our_reader_finds_everything_pandoc_finds`). Hiện skip với lý do "F05 chưa có". Khi F05 xong, nó tự chạy và so từng đoạn: **chữ nào pandoc tìm ra mà bộ đọc của ta không tìm ra thì đó là bug của ta**, báo kèm nguyên văn đoạn bị mất.

### Pandoc được dùng để làm gì, và không dùng để làm gì

| | |
|---|---|
| **Dùng để** | Làm trọng tài. Mượn nhiều năm xử lý ca biên của nó dưới dạng **test** |
| **Không dùng để** | Làm bộ chuyển đổi. Nó bỏ cái không biểu diễn được một cách **im lặng** và trả về 0, trong khi §6.4 đòi bộ chuyển đổi phải **biết** lúc nào nó hạ cấp, để giữ construct đó thành khối `raw` kèm XML gốc và lý do |

Không có file nào trong `specctl/` import pandoc. Nó chỉ tồn tại trong `tests/`.

---

## 6. Kiểm chứng hai nguyên tắc bằng máy

Hai thứ này không phải lời hứa, mà là test:

```bash
pytest tests/test_netguard.py -v       # không có kết nối mạng nào
pytest tests/test_determinism.py -v    # chạy lại ra kết quả giống từng byte
```

Chặn mạng là `autouse` cho **cả bộ test**, không chỉ cho test nào nghĩ tới nó. Một thư viện thêm vào sau này chạm mạng đúng một lần trước khi có test đỏ.

---

## 7. Khi có gì sai

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| `ModuleNotFoundError: specctl` | Chưa `pip install -e ".[dev]"`, hoặc chưa activate venv |
| `ModuleNotFoundError: hypothesis` | Cài thiếu extra `[dev]` |
| `tomllib` không có | Python < 3.11 |
| `... is not a readable .docx package` | File `.docx` bị hỏng zip — kiểm tra `.gitattributes` còn dòng `*.docx binary` không, rồi clone lại |
| Test fixture đỏ sau khi thêm file | Đọc thông báo: nó nêu đúng construct thiếu và cách thêm trong Word |
| Test đỏ ngẫu nhiên, lúc xanh lúc đỏ | Báo lại — bộ test này phải tất định; một test chập chờn là một bug thật |

Chạy một test đang đỏ với chi tiết đầy đủ:

```bash
pytest tests/test_fixtures.py::test_each_present_fixture_contains_what_it_promises -vv
```

---

## 8. Sau khi mọi thứ xanh

Bước tiếp theo là **F06** (đánh số mục) và **F07** (chia file theo section), cả hai đọc luồng khối mà F05 phát ra.

Việc đáng làm trước cả hai: đặt 3 file `.docx` vào `tests/fixtures/`. 14 test đang skip sẽ chạy, trong đó có `test_our_reader_finds_everything_pandoc_finds` — trọng tài độc lập duy nhất của bộ đọc.

Thứ tự đầy đủ các feature: `F-features.md`.
