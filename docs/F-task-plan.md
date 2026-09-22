# specctl — Review E và Task Plan thực thi

**Đối tượng review:** `E-review.md`
**Đối chiếu:** `D-implementation-spec.md` v2.0
**Mục đích:** (1) đánh giá bản review E, (2) chuyển nó thành task list thực thi được, có phụ thuộc và có điều kiện chặn rõ ràng.

---

## Phần 1 — Review bản E-review.md

### 1.1 Kết luận

E là một bản review **tốt và dùng được ngay**. Nó làm đúng việc quan trọng nhất mà một bản review kiến trúc phải làm: buộc mỗi requirement phải trả lời câu "mày chặn rủi ro nào", rồi xếp thứ tự theo phụ thuộc kỹ thuật thay vì theo lịch.

Điểm giá trị cao nhất của E là mục 4, câu cuối: **`validate` phải xong trước khi agent được sửa file**. Spec D (§21.1) xếp W2 D7–D8 viết skill sửa, W2 D9 mới làm validate — tức là cho AI sửa spec hợp đồng trong hai ngày mà không có lớp phát hiện nào. E phát hiện đúng, và đây là loại lỗi mà nếu không sửa thì mọi thứ khác không còn ý nghĩa.

10 defect E nêu ở mục 3: tôi đã đối chiếu từng cái với văn bản D. **Tất cả đều là lỗi thật**, không có cái nào là đọc sai. Ba cái nghiêm trọng nhất đã kiểm chứng trực tiếp:

| E nêu | Kiểm chứng trên D |
|---|---|
| #1 Split tạo trạng thái mâu thuẫn | §5.4 L3 nói `split_from` MUST có trên **mọi** phần, rồi ngay câu sau nói MAY omit nếu giữ ID gốc. Tệ hơn: Appendix D (dòng 1637) cho `SYS-000130` giữ anchor như block sống, còn §7 (dòng 541) ghi cùng ID đó là `status: "split"` — trạng thái terminal. Một ID không thể vừa active trong vault vừa terminal trong registry. E chẩn đoán chính xác |
| #2 V04b báo lỗi sai cho mọi split | §12.5 dòng 1076 đưa cả `split_from` vào tập `claimed`, dòng 1087 báo V04b cho "claimed more than once". Split thành N phần → N block claim cùng ID gốc → luôn lỗi. Mà L2 lại chỉ định nghĩa V04b cho `supersedes`. Xác nhận |
| #3 `validate` ghi `meta/ids.json` | §12.5 dòng 1090 "On a clean run the registry is updated". Validator có side-effect, lại được §20 gắn vào pre-commit hook. Vi phạm chính nguyên tắc determinism §9.5 mà D tự đặt ra. Xác nhận |

#4 cũng xác nhận đầy đủ: §16 chạy `specctl index` ở bước 9 (sau commit bước 8), trong khi hook §20 chạy `index --check` — hook sẽ fail ở mọi lần commit. Và `log.md` cần short SHA (§13.4) nên luôn sinh ra file chưa commit.

### 1.2 Chỗ tôi không đồng ý với E

**(a) Tầng 4 của E xếp V06, V08, V11, V13, V17 vào diện hoãn được.** Tôi cho là sai về chi phí/lợi ích. Lý do E đưa ra — "phần lớn đã được `fmt` tự sửa" — chỉ đúng cho V09/V15/V16 (đúng là `fmt --check` nói lại). Còn lại:

- **V08** (asset được tham chiếu phải tồn tại trên đĩa) chặn R1 trực tiếp: hình mất file thì nội dung mất thật, và không có `fmt` nào sửa được.
- **V11** (block không có anchor) là tiền đề để `--assign-ids` dùng được. Không có V11 thì không biết chỗ nào cần cấp ID.
- **V13** (thiếu `^id` trên link target) làm wikilink chết — đúng cái R2 mà E xếp V01–V03/V07 vào tầng 3 để chặn.
- **V06, V17** mỗi cái khoảng 20 dòng code.

Đề xuất: promote V06, V08, V11, V13, V17 vào bước `validate` lõi. Chỉ hoãn V09, V12, V14, V15, V16.

**(b) E xếp `fmt` ở bước 7, sau khi Problem A đã dùng được ở bước 6.** Vấn đề: front matter dẫn xuất (`breadcrumb`, `order`, `path_ids`, `blocks`, `words`) do `fmt` sở hữu, nhưng `ingest` cũng phải ghi chúng, và `index` cũng phải đọc/tính chúng. Theo thứ tự của E thì cùng một logic được viết ở ingest writer (bước 3), rồi viết lại ở `fmt` (bước 7) — đúng cái lỗi "mỗi nơi tự viết" mà chính E cảnh báo ở tầng 1 cho hàm text.

Đề xuất: đưa toàn bộ derived computation vào **core lib** (bước 2), rồi `ingest writer`, `fmt` và `index` đều gọi nó. `fmt` trở thành lớp mỏng, và vị trí của nó trong thứ tự không còn quan trọng.

### 1.3 Chỗ E bỏ sót

**(a) Defect thứ 11: V05 xung đột với FMT-12.** V05 yêu cầu block `locked:true` **byte-identical** với base. FMT-12 lại cho `fmt` normalize thứ tự attribute trong anchor. Nếu `fmt` đổi thứ tự attribute trên một locked block, V05 báo lỗi trên block không ai sửa. Cần định nghĩa lại V05: so sánh byte các **dòng nội dung** của block (không tính dòng anchor), cộng với so sánh **tập** attribute của anchor không kể thứ tự.

**(b) Bước 1 của E không chạy được ở trạng thái repo hiện tại.** E bắt đầu bằng "thử fidelity trên file thật". Repo chưa có `source/`, chưa có `SYS.docx`, và cả ba input [OWNER-1/2/3] đều chưa có. Hệ quả thực tế: bước 1 **không** được chặn đường vào việc; core lib (bước 2) và fixture phải khởi động song song ngay, rồi spike chạy trên fixture trước và chạy lại trên file thật khi có.

**(c) Fixture của D không sản xuất được.** §18.3 yêu cầu `constructs.docx`, `revisions.docx`, `containers.docx`, `degraded.docx` "hand-authored in Word" và commit vào git. Word không có trong môi trường phát triển, agent không tạo được, và file nhị phân do tay làm thì không reproducible. Nhưng `w:sdt`, `w:ins`/`w:del`, TOC field, merged cell, text box — tất cả đều **viết được bằng XML thuần**. Đề xuất: một helper sinh .docx bằng cách ghi trực tiếp `document.xml` vào zip. Việc này mở khoá T-ING-01/10/11/12 và biến fixture thành code review được. Đây là task riêng, và nó chặn kha khá thứ phía sau.

**(d) Hai model of truth trong dependency.** Appendix E khai cả `python-docx` và `lxml`. Nhưng object model của `python-docx` **che** đúng những thứ walker §10.5 cần thấy: `w:sdt`, `mc:AlternateContent`, `w:ins`/`w:del`. Viết walker trên `python-docx` là tự tạo ra R1. Đề xuất: walker dùng `lxml` trực tiếp trên `document.xml`; `python-docx` chỉ để tiện lấy media/package, hoặc bỏ hẳn.

**(e) Rủi ro license của OMML2MML.XSL.** E có nhắc ở tầng 4. Nói rõ hơn: stylesheet đó là tài sản của Microsoft, vendor vào một package sẽ giao hàng cho customer là rủi ro pháp lý thật, không phải rủi ro kỹ thuật. Đã có fallback bằng hình → nên viết converter subset thuần Python hoặc hoãn hẳn, đừng vendor.

**(f) `fmt` phải hai pha.** FMT-04 nói `^id` là bắt buộc trên block **là target của wikilink ở bất kỳ đâu trong vault**. Nên `fmt` không thể xử lý file theo từng file: pha 1 quét toàn vault thu tập link target, pha 2 mới ghi. §11.3 có nói `fmt` load cả vault, nhưng không nói rõ tính hai pha này — dễ implement sai thành một pha.

### 1.4 Đánh giá phần cắt giảm

Phần tầng 4/tầng 5 của E là phần tôi đồng ý nhất và cũng là phần có giá trị kinh tế cao nhất.

- **Hoãn render shape qua LibreOffice**: đúng. §10.7 match ảnh với object "theo thứ tự xuất hiện" là một giả định về hành vi của LibreOffice, không phải một hợp đồng. Đường degrade đã an toàn về dữ liệu. Thiếu hình minh hoạ là thiếu tiện nghi, không phải mất nội dung.
- **Hoãn re-ingest**: rất đúng, và lý do E đưa ra mạnh hơn lý do "hiếm dùng" — spec D **chưa giải quyết** việc re-ingest ghi đè edit. Làm tính năng đó bây giờ là xây một cái nút xoá công sức Problem B.
- **Cắt performance budget**: đúng. 1200 block là không đáng kể.

---

## Phần 2 — Task list

Thứ tự là thứ tự phụ thuộc, không phải lịch. Mỗi task chỉ dùng cái các task trước đã tạo ra.

| # | Task | Phụ thuộc | Điều kiện chặn |
|---|---|---|---|
| **P0** | Chốt spec amendments cho 11 defect → `F-spec-amendments.md` | — | — |
| **P1** | Scaffold package + CLI + config + CI gate (no-network, determinism) | — | — |
| **P2** | Core lib: model, textutil, parser/serializer round-trip, schemas, **derived tree** | P0, P1 | — |
| **P3** | Fixture builder: sinh .docx bằng raw OOXML | — | — |
| **P4** | Spike fidelity → go/no-go DEC-01 | P3 | `source/SYS.docx`, [OWNER-1] |
| **P5** | Ingest lõi: package, walker, numbering, segment, ID, writer | P2, P3 | — |
| **P6** | Bảng + total-capture + fidelity + coverage.json + gates | P5 | — |
| **P7** | Cross-ref → wikilink | P6 | — |
| **P8** | `specctl fmt` (lớp mỏng trên P2) | P2 | — |
| **P9** | `index.md` + `coverage.md` + `CLAUDE.md` + 3 skill đọc | P6, P7 | **[OWNER-3]** |
| **P10** | `specctl validate` lõi + lineage + merge-base | P0, P8 | — |
| **P11** | `--assign-ids` + `registry sync` tách riêng | P10 | — |
| **P12** | Edit workflow + skill sửa | P10, P11 | **[OWNER-2]** |
| **P13** | `log` + `export xlsx` | P10, P12 | — |
| **P14** | Tầng 4: backlinks, shapes, equations, rule còn lại, hook, eval | tuỳ mục | — |
| **P15** | Tầng 5: re-ingest | P0 | Có nhu cầu thật + thiết kế hợp nhất |

### Ba khác biệt so với thứ tự của E

1. **P0 lên trước mọi dòng code.** Defect #1, #2, #3 thay đổi chính data model và semantics của `validate`. Sửa sau khi đã code là viết lại.
2. **P3 (fixture builder) là task hạng nhất, không phải phụ lục test.** Nó chặn P5 và P4. Không có fixture sinh được bằng code thì không test được walker, mà walker là nơi R1 xảy ra.
3. **P4 (spike) không chặn P1/P2/P3.** Vì source file và [OWNER-1] chưa có, ba việc không phụ thuộc file thật phải chạy ngay. Nhưng P4 vẫn chặn quyết định DEC-01: nếu coverage không đạt thì P5 trở đi phải xem lại trước khi tiếp.

### Điều kiện chặn tuyệt đối

> **P10 (`validate`) phải xong trước P12 (agent sửa file).**

Đây là kết luận của E và tôi giữ nguyên, không nới. Lý do: V10 (numeric/unit diff) là tuyến phòng thủ duy nhất chống R3. Cho agent sửa spec hợp đồng trước khi có nó là chấp nhận rủi ro không đo được, để đổi lấy vài ngày lịch.

### Ba input của owner, theo mức độ khẩn

| Input | Chặn task | Chi phí nếu thiếu |
|---|---|---|
| **[OWNER-3]** cloud-model policy | P9 | Rẻ nhất để có (một dòng ghi nhận), chặn sớm nhất. Thiếu nó thì không được mở session agent nào trên nội dung thật |
| **[OWNER-1]** fidelity metric + threshold | P4 | Không có pass mark thì spike không kết luận được, DEC-01 treo |
| **[OWNER-2]** `target-structure.md` + ví dụ before/after | P12 | Không có ví dụ thật thì `restructure-section` không viết được. Đến P12 mới cần, nên còn thời gian |
