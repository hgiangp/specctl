# specctl — Bản ghi nhận quyết định về hợp đồng dữ liệu

**Tính năng:** F01 (`F-features.md`) · **Áp vào:** `D-implementation-spec.md` v2.0 → v2.1
**Trạng thái:** đã chốt và đã áp vào D

Đặc tả kỹ thuật v2.0 có tám chỗ tự mâu thuẫn hoặc đặc tả một thứ không thực thi được. Mỗi chỗ đều nằm ở phần cốt lõi — định danh, lineage, kiểm tra ghi — nên phải chốt trước khi viết dòng code nào; sửa sau là viết lại.

Tài liệu này ghi **quyết định và lý do**. Bản thân quy tắc đã được viết vào D v2.1 — D vẫn là văn bản chuẩn duy nhất, tài liệu này không chuẩn, chỉ để tra "vì sao lại thế".

Không có quyết định nào ở đây mở rộng hay thu hẹp phạm vi. Tất cả đều chỉ làm cho một quy tắc đã tồn tại trở nên dùng được.

---

## Quyết định 1 — Mọi phần sau khi tách nhận ID mới

### Vấn đề

v2.0 nói hai điều không thể cùng đúng:

- §5.4 L3: `split_from` phải có trên **mọi** phần sau khi tách — rồi ngay câu sau: một phần **được phép** giữ ID gốc và bỏ `split_from`.
- Appendix D cho `SYS-000130` giữ nguyên comment ID như một khối đang sống, trong khi §7 ghi đúng ID đó là `status: "split"` — một trạng thái kết thúc.

Một ID không thể vừa đang sống trong vault vừa đã kết thúc trong sổ đăng ký. Không có consumer nào đọc được trạng thái đó: bộ kiểm tra thấy ID còn trong vault nên coi là `active`; bộ xuất Excel đọc sổ thấy `split` nên xếp vào nhóm đã tách; sổ thì ghi `split_into` chứa cả ID của chính nó hoặc không chứa — cả hai đều sai.

### Quyết định

**Mọi phần sau khi tách đều nhận ID mới và đều mang `split_from:<id-gốc>`. ID gốc biến mất khỏi vault**, chuyển sang trạng thái `split` với `split_into` liệt kê đủ các phần. Tách thành N phần thì tiêu N ID mới và cho một ID nghỉ.

### Vì sao chọn cách này

Cách còn lại — cho phần đầu giữ ID gốc — trông như tiết kiệm ID, nhưng:

- **Trạng thái kết thúc phải có nghĩa là "không còn trong vault".** Nếu không thì không có cách nào kiểm tra tính nhất quán của sổ, vì mọi ID đều có thể ở bất kỳ trạng thái nào.
- **Bản Excel giao customer sẽ báo sai.** Phần giữ ID gốc sẽ được xếp `unchanged` vì ID còn đó, trong khi văn bản của nó rõ ràng đã ngắn đi — một nửa nội dung chuyển sang phần khác. Customer đọc thấy "không đổi" ở một dòng mà nội dung đã đổi.
- **ID rẻ.** Sáu chữ số, không tái sử dụng, một tài liệu khoảng 1200 khối. Tiêu thêm vài ID mỗi lần tách là không đáng kể so với một trạng thái không diễn giải được.

### Trích dẫn cũ có chết không

Không. Đó chính là lý do tồn tại của lineage: sổ đăng ký giữ `SYS-000130` với `split_into: [...]`, nên một trích dẫn tới ID đã nghỉ vẫn tra ra được nội dung đã đi đâu. Đây là cái mà `deleted` không có và `split` có.

### Hệ quả phát sinh — phải sửa thêm một chỗ

Quyết định này làm lộ một lỗi mới ở §12.6 N4. v2.0 nói mỗi khối có lineage được so với "hợp của văn bản các khối tổ tiên". Khi mọi phần tách đều là khối mới, quy tắc đó có nghĩa: **từng phần** được so riêng với khối gốc. Kết quả:

> Gốc chứa `100 Hz`. Tách thành phần A (`100 Hz`) và phần B (`200 ms`).
> Phần B so với gốc → báo "mất 100 Hz, thêm 200 ms". Báo sai.

Sai này xảy ra ở **mọi** lần tách — mà tách là việc hay làm nhất của việc 2. Một công cụ báo sai liên tục sẽ bị bỏ qua, và khi đó nó vô dụng.

**Sửa:** lineage **gom nhóm** trước khi so. Một lần tách là **một** phép so: hợp của **tất cả** các phần, so với văn bản gốc, báo một phát hiện duy nhất mang tên ID gốc. Một lần gộp cũng vậy: khối còn lại so với hợp của các khối bị hấp thu.

---

## Quyết định 2 — Kiểm tra trùng khai báo chỉ áp cho việc gộp

### Vấn đề

§12.5 đưa cả `supersedes` và `split_from` vào cùng một tập `claimed`, rồi báo lỗi V04b cho "ID bị khai nhiều hơn một lần". Nhưng tách thành N phần thì hiển nhiên có N khối cùng khai một ID gốc — theo đúng L3 yêu cầu.

Nghĩa là: **mọi lần tách đều báo lỗi V04b**, và cách duy nhất để tách mà không lỗi là không khai lineage — tức là vi phạm L3 và làm việc tách trông như xoá nội dung.

Ngoài ra §5.4 L2 chỉ định nghĩa V04b cho `supersedes`, nên hai mục nói khác nhau về cùng một quy tắc.

### Quyết định

Tách làm hai tập:

- `superseded` — **multiset** các ID được `supersedes` gọi tên. Bội số > 1 là V04b.
- `split_srcs` — tập các ID được `split_from` gọi tên. **Không bao giờ** áp V04b.
- `claimed` = hợp của hai tập, chỉ dùng để tính "ID này biến mất nhưng đã được lineage giải trình".

### Vì sao

Hai quan hệ có bản số khác nhau, nên không dùng chung một phép kiểm tra được:

| Quan hệ | Bản số | Ý nghĩa nếu trùng |
|---|---|---|
| `supersedes` | nhiều-về-một | Hai khối cùng nói "tôi đã hấp thu khối X" → nội dung của X bị nhân đôi. Đây là lỗi thật |
| `split_from` | một-về-nhiều | N khối cùng nói "tôi sinh ra từ X" → đúng định nghĩa của tách. Đây là trạng thái bình thường |

---

## Quyết định 3 — Công cụ kiểm tra không ghi gì

### Vấn đề

§12.5 v2.0: "chạy sạch thì sổ đăng ký được cập nhật". §12.4: mỗi lần cấp ID thì tăng bộ đếm và ghi một bản ghi.

Nghĩa là `validate` có tác dụng phụ. Nhưng chính D đặt nó vào pre-commit hook (§20) và vào luồng sửa ở hai bước khác nhau (§16). Một công cụ được gọi nhiều lần mà mỗi lần gọi lại thay đổi trạng thái thì:

- chạy hai lần trên cùng một cây làm việc cho hai kết quả khác nhau — vi phạm chính nguyên tắc determinism mà D đặt ra ở §9.5;
- không dùng được trong hook, vì hook không được phép sửa thứ người ta đang commit;
- không debug được, vì lần chạy thứ hai không tái hiện được lần thứ nhất.

### Quyết định

`validate` **chỉ đọc**. Không ghi file section, không ghi `meta/`, không ghi cả file tạm trong repo. Đây là quy tắc duy nhất trong §12 mà không có tham số nào ghi đè được.

Hai việc *có* ghi được tách thành hai lệnh riêng:

| Lệnh | Làm gì | Chạy khi nào |
|---|---|---|
| `specctl assign-ids` | Cấp ID cho khối chưa có comment ID, ghi bản ghi `active` | Trước khi commit, sau khi agent viết khối mới |
| `specctl registry sync` | Ghi trạng thái kết thúc (`merged`/`split`/`deleted`) và `last_seen` | **Sau** khi commit — vì `last_seen` và mối nối lý do trong Excel đều cần một commit đã tồn tại |

Thêm một điều kiện an toàn cho `registry sync`: nó **từ chối chạy** và thoát với mã lỗi nếu `validate` còn báo lỗi trên cùng cây đó. Lý do: sổ đăng ký không bao giờ xoá bản ghi (quy tắc I2), nên một sổ được dựng từ cây có ID trùng hay lineage trỏ sai sẽ ghi sai lịch sử **vĩnh viễn**.

### Kèm theo: tách `assign-ids` khỏi việc tạo file

v2.0 còn một mâu thuẫn nữa ở cùng chỗ này: §12.4 yêu cầu `--assign-ids` "giữ nguyên mọi byte khác của mọi file", trong khi §5.5 yêu cầu chính nó chuyển nội dung sang một file mới. Không có cách nào vừa giữ nguyên mọi byte vừa chuyển nội dung đi.

**Quyết định:** hai lệnh.

- `specctl assign-ids` — chỉ cấp ID, giữ nguyên mọi byte khác, **không tạo, di chuyển, đổi tên hay xoá file nào**. Gặp heading chưa có ID ở cấp cần tách file thì vẫn cấp ID và báo một dòng thông tin chỉ sang lệnh tiếp theo.
- `specctl split-section` — nửa tạo file: tạo file mới, chuyển heading và nội dung sang, ghi phần front matter tự khai, rồi để **toàn bộ** phần dẫn xuất cho lệnh định dạng.

Tách ra mới **kiểm chứng được** cam kết "giữ nguyên mọi byte" bằng một test.

---

## Quyết định 4 — Thứ tự luồng sửa, và cấm squash merge

### Vấn đề

§16 v2.0 xếp: commit ở bước 8, rồi `specctl index` và `specctl log` ở bước 9.

Hai chỗ không chạy được:

1. **Hook fail ở mọi lần commit.** Hook §20 chạy `index --check`. Nội dung đã đổi ở bước 2 nhưng index chỉ được sinh lại ở bước 9, sau commit. Nên ở bước 8 hook luôn thấy index lệch và luôn chặn. Việc đầu tiên người ta làm với một hook luôn chặn là bỏ qua nó — và thế là mất luôn lớp an toàn.
2. **`log` luôn tạo ra file chưa commit.** Mỗi dòng log ghi mã commit ngắn (§13.4), nên nó phải chạy sau commit, nên `log.md` luôn ở trạng thái đã đổi mà chưa commit. Luồng không có bước nào đóng lại việc đó.

Và một chỗ thứ ba, không nằm trong §16 nhưng phá cùng một thứ: **squash merge**. Cột "lý do" trong bản Excel được nối bằng cách tìm dòng log có mã commit là tổ tiên của bản đang xuất (§13.6). Squash thay mã commit đó bằng một mã khác, nên mối nối không tìm thấy gì, và cột lý do **rỗng trong im lặng** — đúng cột duy nhất trả lời "vì sao chỗ này đổi".

### Quyết định

Luồng mới, 14 bước. Ba điểm khác biệt:

- **`specctl index` chạy ở bước 9, trước commit**, và kết quả của nó vào cùng commit với nội dung. Hook qua được vì index đã đúng tại thời điểm commit. (Quy tắc E5)
- **`registry sync` và `log` ở bước 11–12, rồi một commit thứ hai ở bước 13.** Cả hai đều cần một commit đã tồn tại, nên không thể vào commit thứ nhất. Commit thứ hai chỉ chứa `log.md` và `meta/ids.json` — hook vẫn qua, vì cả hai đều không phải đầu ra của `index`.
- **Merge bằng `--no-ff`, cấm squash và cấm rebase-merge.** (Quy tắc E6)

---

## Quyết định 5 — Cách so sánh một khối bị khoá

### Vấn đề

V05 yêu cầu khối `locked:true` phải **giống từng byte** so với bản đối chiếu. Nhưng FMT-12 cho phép lệnh định dạng sắp xếp lại thứ tự thuộc tính trong comment ID, và lệnh định dạng chạy **trước** lệnh kiểm tra trong mọi luồng.

Nên nếu lệnh định dạng đổi thứ tự thuộc tính của một khối bị khoá, V05 báo lỗi trên một khối **không ai sửa**. Một cảnh báo sai trên khối bị khoá là loại cảnh báo tệ nhất: nó nằm đúng chỗ mà người ta cần tin tưởng nhất.

### Quyết định

V05 so đúng hai thứ:

| Phần | So thế nào |
|---|---|
| Các **dòng nội dung** của khối | Từng byte |
| Các **thuộc tính** trong comment ID | Như một mapping khoá→giá trị **không kể thứ tự** |

Bản thân **dòng** comment ID không bao giờ được so từng byte, và dấu tham chiếu khối bị loại hoàn toàn — nó là phần dẫn xuất, lệnh định dạng sở hữu nó.

### Vì sao

V05 tồn tại để bắt một caption hình bị đổi hay một khối hạ cấp bị viết lại. Nó không tồn tại để bắt việc sắp xếp lại thuộc tính — đó chính là việc mà lệnh định dạng được giao làm. Định nghĩa lại theo đúng ý định của quy tắc, thay vì theo một câu chữ không thực thi được.

---

## Quyết định 6 — Section do người viết thêm cần một trường phân biệt

### Vấn đề

Front matter của section có hai trường **bắt buộc và bất biến** mô tả nguồn gốc từ file Word: `source` (tên file và khoảng chỉ số đoạn) và `bookmarks`. Schema yêu cầu `source` là một object có đúng hai chỉ số đoạn.

Nhưng §5.5 cho phép người sửa tạo section mới. Section đó **không có** khoảng đoạn nào trong file Word, vì nó chưa bao giờ ở trong file Word. Không có giá trị nào hợp lệ để điền, và điền số giả thì tệ hơn bỏ trống.

### Quyết định

Thêm một trường bắt buộc `origin`, nhận `ingest` hoặc `authored`. Schema đặt `source` phụ thuộc vào nó:

| `origin` | `source` | `bookmarks` |
|---|---|---|
| `ingest` | object có `docx` và khoảng đoạn | tên bookmark trong section |
| `authored` | `null` | `[]` |

### Vì sao không chọn cách khác

- *Điền `paragraphs: [0, 0]`* — một giá trị giả trông như thật. Bất kỳ đoạn code nào dùng khoảng đoạn để tra lại file gốc sẽ tra sai và không có cách nào biết.
- *Cho `source` thành không bắt buộc* — thì không phân biệt được "section do người viết thêm" với "section từ file gốc mà bộ đọc quên ghi nguồn". Hai thứ đó cần phân biệt được, vì một cái là bình thường và một cái là lỗi.

Trường `origin` nói **ý định**, nên kiểm tra được cả hai chiều.

---

## Quyết định 7 — Bộ bóc số phải có ranh giới

### Vấn đề

Văn phạm v2.0 bắt đầu bằng "một chữ số", không có ranh giới từ. Ba hậu quả trên tài liệu automotive thật:

| Đầu vào | v2.0 bóc ra | Đúng ra phải là |
|---|---|---|
| `Sig2`, `CAN_2`, `A1` | số `2`, `2`, `1` | không có gì — đây là tên tín hiệu |
| `0x1F` | số `0` | không có gì — đây là mặt nạ bit hoặc địa chỉ |
| `1,5` | `15` (bỏ dấu phân cách nghìn) | `1.5` |

Cái thứ nhất tạo ra cảnh báo sai mỗi khi đổi tên tín hiệu. Cái thứ ba **nguy hiểm hơn**: nó làm một thay đổi thật từ `1,5` sang `1,6` được so như `15` với `16` — vẫn bắt được, nhưng báo cáo sai giá trị cho người đọc, và một báo cáo ghi sai số thì không dùng được trong tài liệu audit.

### Quyết định

Bốn quy tắc, tất cả áp trước khi bóc:

1. **Ranh giới trước và sau.** Một chữ số đứng ngay sau chữ cái, chữ số, `_`, `#`, `$` hay `%` không bao giờ mở đầu một token. Dấu `.` hoặc `,` ở cuối chỉ tính là dấu câu khi sau nó là khoảng trắng hoặc hết chuỗi.
2. **Chữ cái dính liền sau số.** Nếu thuộc từ vựng đơn vị thì đó là đơn vị — `50ms` giống hệt `50 ms`. Nếu không thuộc thì **loại cả token** — `1F`, `2x`, `3rd` không ra gì. Có khoảng trắng thì từ đó không phải đơn vị nhưng số vẫn được bóc.
3. **Tiền tố hệ đếm.** Token khớp `0[xXbBoO]…` bị loại hoàn toàn.
4. **Dấu thập phân, quy tắc tường minh.** Dấu phẩy là phân cách nghìn **chỉ khi** khớp đúng `\d{1,3}(,\d{3})+`. Ngược lại nó là dấu thập phân. Có cả `,` và `.` thì dấu **đứng sau** là dấu thập phân. Nếu tài liệu viết thập phân bằng dấu phẩy xuyên suốt thì khai `decimal_comma = true` trong file cấu hình — khai một lần, không bao giờ đoán theo từng token.

---

## Quyết định 8 — Ba chỗ chưa xác định trong phép đo độ trung thực

Phép đo này là **bằng chứng duy nhất** cho thấy bản Markdown đáng tin, nên nó không được có chỗ nào mơ hồ, và không được thổi phồng.

### 8a — Đoạn ngắn làm con số phồng lên

v2.0 tìm kiếm bằng phép "chuỗi con nằm trong chuỗi mẹ", trên phạm vi cả vault. Đoạn nguồn `"Yes"`, `"N/A"`, `"1"`, `"OK"` sẽ khớp ở đâu đó **theo xác suất**. Nghĩa là độ bao phủ tăng theo **kích thước** của vault, chứ không theo lượng nội dung thật sự giữ được — và con số đẹp nhất lại là con số che đúng thứ nó cần phát hiện.

**Quyết định:** đoạn có dạng chuẩn hoá **ngắn hơn 12 ký tự** chỉ được tìm **trong section sở hữu nó**, và chỗ khớp phải có ranh giới không phải chữ-số ở cả hai đầu. Ngưỡng 12 là **cố định**, không cấu hình — cùng lý do với hằng số chia CJK: ngưỡng phải có cùng một nghĩa ở mọi lần chạy, nếu không thì con số không so sánh được giữa hai lần.

Kèm theo: báo cáo phải nêu riêng số đoạn ngắn, số đoạn ngắn đã bao phủ, và độ bao phủ tính riêng cho đoạn dài. Cửa chặn vẫn đặt trên con số tổng — nhưng phần chia nhỏ là cái làm một con số **đạt** trở nên kiểm chứng được.

### 8b — `candidate_sections()` chưa được định nghĩa

v2.0 gọi hàm này trong đoạn mã giả nhưng không định nghĩa nó ở đâu cả.

**Quyết định:** thứ tự là — section sở hữu đoạn nguồn, rồi section cha, rồi các section con, rồi mọi section còn lại theo thứ tự tài liệu. Bước phân section đã gán mỗi đoạn nguồn cho một section, nên "section sở hữu" là một phép tra, không phải một phép tìm. Thứ tự này tồn tại để kết quả khớp đầu tiên là **xác định** và để phép quét rẻ. Với đoạn dài, mọi section đều hợp lệ; với đoạn ngắn, chỉ section sở hữu.

### 8c — Ký tự escape của Markdown

Bộ ghi escape một dấu `|` nằm trong ô bảng thành `\|`. Nếu hàm đổi khối thành văn bản thuần không bỏ escape, thì đoạn nguồn `A|B` **không bao giờ** khớp với `A\|B` đã ghi ra, và một đoạn được giữ nguyên hoàn hảo bị báo là mất.

**Quyết định:** hàm đó phải bỏ escape ở bước cuối — xoá dấu `\` đứng ngay trước một trong `| * _ [ ] < >` và dấu backtick, và `\\` thành một dấu `\`.

---

## Phần bổ sung — ba lỗi format phát hiện khi implement (D v2.2)

Ba lỗi dưới đây không nằm trong tám điểm ban đầu. Chúng lộ ra khi viết bộ đọc/ghi file section (F03), và lộ ra theo cùng một cách: **một file hợp lệ không sống sót qua vòng ghi rồi đọc lại**.

### Quyết định 9 — Section front-matter ở `level: 1`, không phải `level: 0`

§10.9 cho section chứa nội dung trước heading đầu tiên `level: 0`. Nhưng §6.1 quy định dòng heading có từ một đến sáu dấu `#`. Nên **level 0 không có dòng heading nào biểu diễn được**: section đó dựng được trong bộ nhớ, ghi ra file, rồi không đọc lại được nữa — bộ đọc thấy một dòng không phải anchor cũng không phải heading và báo "nội dung không có anchor".

Đây là section chứa **lịch sử phiên bản**, tức nội dung hợp đồng. Một lỗi làm mất đúng nó là loại lỗi tệ nhất.

Lỗi thứ hai của `level: 0`, ít rõ hơn nhưng ảnh hưởng rộng hơn: nó làm phần front matter trở thành **tổ tiên của mọi chương**. Mọi breadcrumb trong vault sẽ có tiền tố `SYS > Front matter >`. Lịch sử phiên bản không phải cha của chương 3.

**Chốt:** `level: 1`, với một dòng heading thật (`# Front matter`), không có số mục. Nó trở thành **em ruột** của chương 1 — đúng bản chất của nó. Kèm theo: schema A.1 đổi `level` tối thiểu từ 0 thành 1, vì một level không biểu diễn được thì không nên hợp lệ.

Bộ ghi cũng được đặt chốt chặn: gặp khối heading không có dòng ATX thì **từ chối ghi** thay vì ghi ra một file không đọc lại được. Thà lỗi to và sớm hơn là mất nội dung âm thầm.

### Quyết định 10 — Khối heading đúng một dòng

Văn phạm §6.1 viết `heading-block = heading-line , { LF , content-line }`, tức cho phép có dòng nội dung sau dòng heading. Nhưng §6.3 nói heading là "one ATX heading line", và Appendix D cũng vậy. **Chốt:** đúng một dòng, sửa văn phạm theo §6.3.

### Quyết định 11 — Quy tắc style YAML

§10.11 viết "flow style only for `source`", trong khi **cả hai** khối front matter mẫu (§6.2 và Appendix D) dùng flow cho `path`, `path_ids`, `bookmarks` và `refs_out`. Không thể vừa đúng cả hai.

**Chốt:** thay bằng một bảng nêu rõ từng loại giá trị dùng style nào, khớp với hai ví dụ mẫu đến từng ký tự. Và quy tắc quote được nêu chính xác: một scalar chỉ để trần khi nó khớp `^[A-Za-z0-9][A-Za-z0-9 _-]*$` **và** không phải giá trị mà một bộ đọc YAML có thể hiểu thành số, boolean hay null.

Điểm đáng nêu: phép thử thứ hai áp cho **cả YAML 1.1 và 1.2**, không chỉ cho phương ngữ mà thư viện của chính chúng ta hiện thực. `1e5` là **chuỗi** với bộ đọc YAML 1.1 và là **số thực 100000.0** với bộ đọc YAML 1.2. Vault được đọc bởi Obsidian và các editor, không chỉ bởi `specctl`. Quote thêm thì không mất gì; để người xem đọc ra một giá trị khác với cái mà công cụ kiểm tra đọc ra là một sự bất đồng âm thầm về việc spec nói gì.

*Phát hiện này là do test: một test đối chiếu `emit_scalar` với bộ đọc YAML thật đã báo `1e5` để trần, và cái làm lộ vấn đề không phải là bộ đọc của chúng ta mà là câu hỏi "bộ đọc nào".*

---

## Tổng hợp thay đổi trong D v2.1

| Quyết định | Mục đã sửa trong D |
|---|---|
| 1 · Tách khối | §5.4 L3, §7, §12.6 N4, §14, §15, Appendix D |
| 2 · V04b | §5.4 L2, §12.3, §12.5 |
| 3 · Chỉ đọc, tách lệnh | §9.1, §9.5, §12.1, §12.4, §12.5, §12.9, §12.10, Appendix E |
| 4 · Thứ tự luồng | §16 (E5, E6), §20 |
| 5 · Khối bị khoá | FMT-08, §6.3, §12.3, §12.8 |
| 6 · `origin` | §5.5, §6.2, Appendix A.1, Appendix D |
| 7 · Bóc số | §9.2, §12.6 |
| 8 · Độ trung thực | §6.6, §8, §10.12 (F7–F9) |

| 9 · Section front-matter level | §10.9, Appendix A.1 |
| 10 · Heading một dòng | §6.1 |
| 11 · Style YAML | §10.11 |

Test mới kèm theo: T-ING-03b, T-ING-03c, T-VAL-06b, T-VAL-06c, T-VAL-07b, T-VAL-10, T-VAL-11, T-VAL-12, T-VAL-13.

Trong đó **T-VAL-12** là test canh nguyên tắc: băm toàn bộ repo trước và sau mỗi lần gọi `validate` và mỗi lần gọi có `--check`, rồi so. Nó là cách duy nhất để quyết định 3 không bị xói mòn dần bằng những lần "ghi tạm một file cho tiện".

---

## Phần bổ sung — một lỗi phép đo phát hiện khi implement F05 (D v2.3)

### Quyết định 15 — Phía nguồn của phép đo độ trung thực phải khử trùng lặp text box

#### Vấn đề

§10.12 bước 1 nói: "for p in every paragraph and table cell in scope". Đọc thẳng câu đó
rồi gom `w:t` của từng đoạn thì **một text box chứa một câu sinh ra ba đoạn nguồn**:

| Đoạn | Nội dung | Vì sao có |
|---|---|---|
| 1 | câu đó, **lặp hai lần dính liền nhau** | Đoạn *bọc ngoài* text box. Các đoạn bên trong box nằm lồng trong nó, nên phép gom `w:t` của đoạn ngoài nuốt luôn cả hai nhánh |
| 2 | câu đó | Nhánh `mc:Choice` — DrawingML |
| 3 | câu đó | Nhánh `mc:Fallback` — VML |

Word ghi mọi text box theo đúng cách này, không phải ca hiếm.

Đoạn 1 là chuỗi **không tồn tại ở bất kỳ đâu trong tài liệu**. Không bộ ghi nào phát ra
được nó, nên nó vĩnh viễn nằm trong danh sách "chưa bao phủ". Hệ quả: ACC-2 tụt khoảng
một đoạn cho mỗi text box, và danh sách `uncovered` của §10.12 F5 — thứ đáng ra phải
hành động được — có một dòng mà không ai sửa được.

Đây đúng là điều F1 cảnh báo, nhưng ở chiều ngược lại: không phải con số bị **thổi
phồng**, mà bị **bóp xuống** bởi chính cách đếm. Cả hai đều làm con số mất nghĩa.

#### Quyết định

F4 nói "text phát ra hai lần đếm một lần ở phía nguồn". Câu đó đúng nhưng chưa đủ: nó nói
về *kết quả*, không nói *cách tính*. Bổ sung vào F4 phần bắt buộc:

- lấy **đúng một nhánh** của `mc:AlternateContent` — `mc:Choice`, không có thì `mc:Fallback`;
- **loại** chữ nằm trong `w:txbxContent` ra khỏi phần chữ của đoạn bọc ngoài nó.

Text box vì vậy đóng góp đúng một đoạn nguồn.

#### Vì sao ghi lại thay vì sửa lặng lẽ

Phát hiện này không nằm trong phạm vi F05 — nó là phép đo của F11. Nhưng nó lộ ra ở F05
vì đây là lúc đầu tiên có một bộ đọc thật để so. Nếu không ghi lại, người làm F11 sẽ viết
đúng cái vòng lặp ngây thơ mà §10.12 bước 1 gợi ý, rồi mất một ngày tìm xem tại sao độ
bao phủ thấp hơn dự kiến trên tài liệu thật — mà nguyên nhân nằm ở phía nguồn, chỗ không
ai nghĩ tới, vì phía nguồn "chỉ là đọc file gốc".

Test đi kèm: `test_a_text_box_is_one_source_segment_not_three`.

#### Một điểm nữa, cùng gốc — công cụ trọng tài phải dùng chung định nghĩa phạm vi

`source_segments()` trong `tests/test_pandoc_oracle.py` không lọc mục lục, trong khi
§10.12 F2 nói rõ mục lục **ngoài phạm vi** và §10.5 W4 bỏ nó có ghi nhận. Pandoc phát ra
các dòng mục lục như đoạn văn thường, nên khi `containers.docx` có mặt, test oracle sẽ
báo bộ đọc của ta "làm mất" đúng những dòng mà đặc tả bảo phải bỏ.

Đã sửa: hàm đó nay dựng tập đoạn mục lục từ chính OOXML — cả hai dạng W4 nêu (field phức
mở ở một đoạn và đóng ở đoạn sau, và style `TOC1`…`TOC9`). Tính độc lập với bộ ghi được
giữ nguyên: nó **không** hỏi walker của ta cái gì trong phạm vi, vì một trọng tài lấy câu
trả lời từ bên bị xử thì không chứng minh được gì.
