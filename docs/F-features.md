# specctl — Vấn đề, phương pháp, và thứ tự tính năng

**Trạng thái:** bản kế hoạch đang có hiệu lực · **Người đọc:** owner, implementer, coding agent
**Cách dùng:** đọc hết tài liệu này là hiểu được đang giải bài gì, giải bằng cách nào, và làm cái gì trước.
Chi tiết kỹ thuật từng quy tắc nằm ở `D-implementation-spec.md`. Tài liệu này quyết định **làm gì và theo thứ tự nào**; D quyết định **làm chính xác ra sao**.

---

# Phần I — Vấn đề

## 1. Hiện trạng

Chúng ta có **một** file Word: bản đặc tả yêu cầu hệ thống (SYS spec, lĩnh vực automotive, theo ASPICE SYS.2) do customer Nhật giao, đã dịch sang tiếng Anh theo bản thoả thuận. File được cấu trúc tốt bằng heading, nhưng bên trong có đủ thứ: văn bản, bảng có merge cell, hình ảnh, shape và text box của Word, công thức toán, và tham chiếu chéo nội bộ.

Đây là **tài liệu hợp đồng**. Một con số sai trong đó là một cam kết sai với customer.

## 2. Hai việc cần làm được

| | Việc 1 — Đọc hiểu | Việc 2 — Cải thiện |
|---|---|---|
| Câu hỏi | Spec nói gì về X? Chỗ nào tham chiếu tới nó? | Sửa lại cấu trúc và cách trình bày cho tốt hơn |
| Ai làm | AI agent trả lời | AI agent sửa, người review |
| Kết quả mong muốn | Câu trả lời có trích dẫn, kiểm chứng được | Bản spec tốt hơn, kèm bằng chứng đã đổi những gì |

Việc 2 phụ thuộc việc 1: chưa định vị được nội dung thì chưa sửa được nội dung.

## 3. Vì sao việc này khó — bốn cách thất bại

Toàn bộ thiết kế tồn tại để chặn bốn thứ dưới đây. Đây là thang đo duy nhất để đánh giá mọi tính năng: **tính năng nào không chặn được cái nào trong bốn cái này thì cắt được.**

### Thất bại 1 — Mất nội dung lúc chuyển đổi, mà không ai biết

Bộ đọc file Word âm thầm bỏ sót một đoạn văn, một bảng, hay chữ trong text box. Hoặc tệ hơn: đưa cả đoạn văn **đã bị xoá** (track changes chưa accept) vào như thể đó là yêu cầu còn hiệu lực.

*Hậu quả:* bản chuyển đổi không còn đúng với spec gốc. Mọi câu trả lời và mọi bản sửa dựa trên nó đều sai, và không có dấu hiệu nào báo.

Đây là thất bại nguy hiểm nhất, vì nó **im lặng**. Một bộ đọc viết cẩu thả chỉ gom chữ và vẫn chạy trót lọt.

### Thất bại 2 — Không có địa chỉ ổn định

Nội dung chỉ được định vị bằng "dòng 412" hoặc "mục 3.2". Cả hai đều thay đổi mỗi lần có người sửa: chèn một mục mới là toàn bộ số mục phía sau lệch hết.

*Hậu quả:* không trích dẫn được, không so sánh được hai phiên bản, không có khoá dòng cho file Excel giao cho customer.

### Thất bại 3 — AI âm thầm đổi nội dung

Agent đổi `50 ms` thành `80 ms`. Hoặc đổi `mV` thành `MV` — lệch chín bậc. Hoặc bỏ mất một câu khi viết lại đoạn văn cho gọn.

*Hậu quả:* spec hợp đồng bị sai, và người review diff không phát hiện vì diff dài và trông hợp lý.

### Thất bại 4 — Không chứng minh được đã đổi những gì

Customer hỏi: "cái gì đã đổi, so với bản nào, và vì sao?" Không trả lời được.

*Hậu quả:* không giao được hàng, không audit được.

---

# Phần II — Phương pháp

## 4. Ý tưởng cốt lõi

> **Biến file Word thành một tập file Markdown, trong đó mỗi khối nội dung mang một mã ID bất biến. Tập file đó trở thành bản gốc để làm việc. Mọi lần AI ghi vào nó đều phải đi qua một cửa kiểm tra tự động trước khi người duyệt.**

Cụ thể là năm quyết định, mỗi quyết định nhắm vào một thất bại ở mục 3:

### 4.1 Mỗi khối nội dung có một ID bất biến — chặn thất bại 2

Mỗi đoạn văn, bảng, hình, danh sách nhận một mã dạng `SYS-000121` ngay lúc chuyển đổi. Mã này **không bao giờ đổi** khi nội dung sửa, khi vị trí đổi, khi số mục được đánh lại. Mã nằm ngay trong file, dưới dạng một comment Markdown:

```markdown
<!-- id:SYS-000121 type:paragraph -->
Hệ thống phải tác động lực phanh trong vòng 50 ms sau khi tín hiệu bàn đạp
vượt ngưỡng định nghĩa tại [[SYS-000245|5.1 Signal thresholds]].
```

ID là nền móng của mọi thứ còn lại: trích dẫn được, so sánh hai phiên bản được, làm khoá dòng Excel được. Không có nó thì không có hệ thống.

### 4.2 Nguyên tắc "không bao giờ biến mất" — chặn thất bại 1

Có những thứ trong Word không thể biểu diễn bằng Markdown: SmartArt, OLE object, bảng cấu trúc quá phức tạp. Với những thứ đó, quy tắc là: **không biểu diễn được thì hạ cấp, tuyệt đối không bỏ.**

Nội dung hạ cấp trở thành một khối `raw` bị khoá, mang theo phần chữ trích được và toàn bộ XML gốc lưu ra file riêng, kèm một ghi chú nêu lý do. Nghĩa là "chưa xử lý được" không bao giờ trở thành "đã mất".

### 4.3 Đo độ trung thực theo một chiều — chặn thất bại 1

Câu hỏi được đo là: **bao nhiêu phần trăm chữ trong file Word gốc tìm thấy được trong bản Markdown?**

Chỉ đo một chiều, và phần chữ mà công cụ *thêm vào* (số mục, số thứ tự danh sách, caption hình) được báo cáo riêng, **không bao giờ bù trừ**. Lý do: nếu dùng tỉ lệ ròng (số ký tự ra chia số ký tự vào) thì một bản chuyển đổi mất 1% đoạn văn và thêm 1% số mục sẽ cho đúng 1.00 — tức là con số đẹp nhất lại che đúng cái nó cần phát hiện.

Con số này là **bằng chứng duy nhất** cho thấy bản Markdown đáng tin. Đi kèm nó là một báo cáo liệt kê từng chỗ chưa bao phủ được, vì một con số thấp mà không nói thấp ở đâu thì không hành động được.

### 4.4 Cửa kiểm tra tự động trước khi người duyệt — chặn thất bại 3

AI không được commit. Luồng là: AI sửa file → công cụ định dạng lại phần dẫn xuất → **công cụ kiểm tra** → người xem diff → người commit.

Công cụ kiểm tra quan trọng nhất là bộ so sánh số và đơn vị. Nó bóc mọi con số kèm đơn vị trong một khối ra thành một **túi giá trị** (multiset), so túi trước với túi sau, rồi báo phần chênh. Cách so này bất biến với việc đảo thứ tự câu — nên viết lại đoạn văn cho gọn thì không báo nhầm — nhưng đổi `50 ms` thành `80 ms` thì luôn bị bắt.

Những khối không review được bằng mắt qua diff văn bản — hình ảnh, shape, khối hạ cấp — bị **khoá cứng**: sửa vào là báo lỗi.

### 4.5 Thay đổi được khai báo, không phải suy đoán — chặn thất bại 4

Việc cải thiện spec chủ yếu là **tách và gộp** các khối. Nếu để công cụ tự suy đoán bằng độ giống nhau của văn bản thì kết quả không xác định và sai ngay khi đoạn văn được viết lại.

Nên quy tắc là: người/agent khi gộp hai khối phải **khai** ngay trong file rằng khối còn lại đã hấp thu khối nào; khi tách thì khai các phần mới sinh ra từ khối nào. Nhờ đó công cụ phân biệt được "nội dung bị xoá" với "nội dung đã chuyển sang khối khác" — và file Excel giao customer báo đúng "đã gộp" thay vì báo sai thành "đã xoá nội dung".

## 5. Vì sao chọn Markdown + git, không phải database

- **Đọc được bằng mắt.** Một file Markdown là bằng chứng tự thân; một bảng trong database thì không.
- **git cho sẵn mọi thứ cần cho thất bại 4:** lịch sử, diff, nhánh, so sánh với một mốc đã đánh dấu.
- **AI agent đọc và sửa file trực tiếp**, không cần xây thêm tầng trung gian nào.
- **Không có hạ tầng nào phải dựng.** Một "vault" chỉ là một thư mục.
- **Không khoá công nghệ.** ID nằm trong dữ liệu, nên sau này muốn thêm index tìm kiếm, graph, hay đổi sang store JSON thì đều cộng thêm được mà không phải làm lại phần đã có.

Đánh đổi: Markdown không biểu diễn được mọi thứ trong Word. Chính vì vậy mới cần mục 4.2 (không bao giờ biến mất) và mục 4.3 (đo và công bố con số).

## 6. Bảy nguyên tắc không thương lượng

Đây là những thứ nếu vi phạm thì phương pháp ở trên mất hiệu lực. Mọi tính năng ở Phần III đều phải tôn trọng chúng.

| # | Nguyên tắc | Vì sao |
|---|---|---|
| 1 | **Không có AI nào trong đường chuyển đổi.** File Word → Markdown là thuần thuật toán | Một câu bị bịa hay bị bỏ trong tài liệu hợp đồng là không chấp nhận được. Cách chứng minh: chương trình không được phép gọi mạng, và có test kiểm tra điều đó |
| 2 | **Chạy lại phải ra kết quả giống từng byte** | Không tái tạo được thì không so sánh được, và không debug được lỗi mất dữ liệu |
| 3 | **File Word gốc không bao giờ bị ghi vào** | Đó là bản đối chiếu cuối cùng |
| 4 | **ID đã cấp thì không bao giờ tái sử dụng** | Tái dùng một ID làm mọi trích dẫn cũ trỏ sai nội dung, âm thầm |
| 5 | **AI không commit. Người review diff là chốt chặn cuối** | Tự động hoá phát hiện được cái đã biết; người phát hiện cái chưa nghĩ tới |
| 6 | **Phần dẫn xuất do công cụ sở hữu, không sửa tay** | Thứ gì nói lại thông tin đã có ở chỗ khác thì sẽ lệch. Agent điều hướng bằng phần dẫn xuất, nên lệch là đi sai mà không có cảnh báo |
| 7 | **Công cụ kiểm tra chỉ đọc, không ghi** | Nó được chạy nhiều lần và chạy trong hook. Có tác dụng phụ thì chạy hai lần ra hai kết quả |

---

# Phần III — Tính năng theo thứ tự ưu tiên

## 7. Cách đọc phần này

Tính năng được chia làm bảy nhóm. Thứ tự nhóm là **thứ tự bắt buộc phải làm**, vì mỗi nhóm chỉ dùng những gì nhóm trước đã tạo ra. Trong cùng một nhóm thì làm song song được.

Mỗi tính năng ghi rõ: làm gì, chặn thất bại nào trong bốn thất bại ở mục 3, và **xong khi nào** — vì "đã làm" không phải là một trạng thái kiểm tra được.

| Nhóm | Tên | Giá trị nhìn thấy được sau khi xong |
|---|---|---|
| **A** | Nền móng | Chưa có gì cho người dùng. Đây là phần mà viết sai thì sai lan ra mọi nơi |
| **B** | Chuyển đổi tin cậy | Chứng minh được bằng số rằng bản Markdown không mất dữ liệu |
| **C** | Agent đọc được | **Việc 1 dùng được**: hỏi spec, nhận câu trả lời có trích dẫn |
| **D** | Kiểm soát ghi | Chưa có gì mới cho người dùng, nhưng là điều kiện để nhóm E được phép tồn tại |
| **E** | Agent sửa được | **Việc 2 dùng được**: cải thiện spec có kiểm soát |
| **F** | Giao hàng | File Excel cho customer |
| **G** | Nên có | Hoãn được không ảnh hưởng ai |

> **Một quy tắc cứng, không nới:** nhóm D phải xong **trước** nhóm E. Bộ so sánh số là tuyến phòng thủ duy nhất chống thất bại 3. Cho AI sửa tài liệu hợp đồng trước khi có nó là chấp nhận một rủi ro không đo được, để đổi lấy vài ngày lịch.

---

## Nhóm A — Nền móng

### F01 · Chốt lại hợp đồng dữ liệu

**Làm gì:** bản đặc tả kỹ thuật hiện tại có một số chỗ tự mâu thuẫn, mà mỗi chỗ đều nằm ở phần cốt lõi. Phải chốt lại thành một câu trả lời duy nhất trước khi viết code, vì sửa sau là viết lại:

1. **Tách khối:** hiện tại vừa cho phép phần đầu giữ ID gốc, vừa ghi ID gốc vào trạng thái "đã tách" — một ID không thể vừa còn sống vừa đã kết thúc. Chốt: mọi phần sau khi tách đều nhận ID mới, ID gốc biến mất khỏi vault và chỉ còn trong lịch sử.
2. **Kiểm tra trùng khai báo:** quy tắc "một ID chỉ được một khối khai" hiện áp dụng cho cả việc tách, nhưng tách thành N phần thì hiển nhiên có N khối cùng khai một ID gốc. Chốt: quy tắc này chỉ áp cho việc gộp.
3. **Công cụ kiểm tra đang ghi vào sổ đăng ký ID** — vi phạm nguyên tắc 7. Chốt: tách việc cập nhật sổ thành một lệnh riêng, chạy sau khi commit.
4. **Thứ tự các bước trong luồng sửa hiện không chạy được:** hook kiểm tra file index trước khi index được sinh lại; file log cần mã commit nên luôn tạo ra file chưa commit. Chốt lại thứ tự, và cấm squash merge vì nó làm mất mã commit — mà mã commit là cái nối bản Excel với lý do thay đổi.
5. **So sánh khối bị khoá:** yêu cầu "giống từng byte" xung đột với việc công cụ định dạng được phép sắp xếp lại thuộc tính trong comment ID. Chốt: so sánh byte phần nội dung, so sánh **tập** thuộc tính không kể thứ tự.
6. **Section mới do agent tạo** không có giá trị hợp lệ cho hai trường bắt buộc mô tả nguồn gốc từ file Word. Chốt: thêm một trường phân biệt "từ file gốc" với "do người viết thêm".
7. **Bộ bóc số đang bắt cả những thứ không phải số đo:** `Sig2` bị bóc thành số 2, `0x1F` thành số 0, và `1,5` bị hiểu thành 15. Chốt lại ranh giới từ và cách xử lý dấu phẩy.
8. **Cách đo độ trung thực** hiện cho đoạn ngắn như "Yes" hay "1" khớp ở bất kỳ đâu, làm con số bị thổi phồng. Chốt độ dài tối thiểu và cách chọn vùng để đối chiếu.

**Chặn:** cả bốn thất bại, ở mức định nghĩa.
**Xong khi:** có một văn bản nêu rõ từng quyết định trên, và không còn chỗ nào trong đặc tả kỹ thuật nói ngược lại.

**Trạng thái: xong.** Quyết định và lý do ở `G-data-contract.md`; quy tắc đã được áp vào `D-implementation-spec.md` v2.1. Quyết định 1 làm lộ thêm một lỗi chưa ai nêu: nếu mỗi phần sau khi tách được so số riêng với khối gốc thì mọi lần tách đều báo sai "mất số" — nên phép so số giờ **gom nhóm** theo lineage, một lần tách là một phép so. Chín test mới đi kèm, trong đó một test băm cả repo trước và sau mỗi lần chạy lệnh kiểm tra, để nguyên tắc "chỉ đọc" không bị xói mòn dần.

### F02 · Khung chương trình

**Làm gì:** cấu trúc package Python, một chương trình dòng lệnh với các lệnh con, cách đọc cấu hình (tham số dòng lệnh → biến môi trường → file cấu hình → giá trị mặc định), quy ước mã thoát, và tham số cố định đồng hồ để chạy lại ra kết quả giống nhau.

Kèm theo — và đây là phần quan trọng hơn cái khung: **hai test hạ tầng có từ ngày đầu.** Một test chặn mọi kết nối mạng và fail nếu có ai gọi ra ngoài (chứng minh nguyên tắc 1 bằng máy, không bằng lời cam kết). Một test chạy cùng đầu vào hai lần rồi so từng byte (nguyên tắc 2). Thêm hai test này về sau thì luôn bị lùi, và khi đó nguyên tắc 1 và 2 chỉ còn là ý định.

**Chặn:** thất bại 1 và 3, ở mức cơ chế.
**Xong khi:** hai test trên chạy trong CI và đang xanh.

**Trạng thái: xong.** 74 test xanh. Vài điểm đáng ghi:

- **Chặn mạng là `autouse` cho cả bộ test**, không chỉ cho test nào nghĩ tới nó. Một thư viện thêm vào sau này chạm mạng đúng một lần trước khi có test đỏ. Bảy test kiểm chính cái guard — vì một guard hỏng mà vẫn im lặng thì còn tệ hơn không có guard.
- **Bộ băm cây có test cả hai chiều:** không chỉ kiểm hai cây giống nhau thì qua, mà kiểm một bộ ghi có timestamp trôi thì **bị bắt**. Cộng thêm các ca cây khác nhau chỉ bởi một thư mục rỗng, hoặc chỉ bởi đích của symlink.
- **Thứ tự ưu tiên cấu hình được test cả bốn nguồn trong một lần chạy**, mỗi giá trị đến từ một nguồn khác nhau, và `--verbose` phải in đúng nguồn của từng cái.
- **Sai chính tả trong file cấu hình là lỗi**, không phải bị bỏ qua — đúng lý do mà quyết định "khai một lần" tồn tại.
- Hai chỗ §9.2 và §9.4 chưa nói rõ đã được bổ sung vào D: `SPECCTL_<NAME>` thì `<NAME>` là gì (bảng ánh xạ đầy đủ), và một lệnh chưa làm thì thoát bằng mã nào — không thêm mã thứ sáu ngoài bảng.

### F03 · Thư viện lõi

**Làm gì:** phần mà mọi lệnh đều dùng, nên viết sai ở đây thì sai đồng loạt.

- **Ba hàm xử lý văn bản** — chuẩn hoá khoảng trắng, đổi một khối thành văn bản thuần, đếm từ — mỗi hàm **đúng một định nghĩa duy nhất**. Bốn nơi cần so sánh văn bản (đo độ trung thực, khoá đối chiếu trong sổ ID, so sánh số, cột nội dung của Excel). Nếu mỗi nơi tự viết thì bốn nơi cho bốn kết quả khác nhau và không ai biết nơi nào đúng. Riêng phần so sánh đơn vị phải **phân biệt chữ hoa chữ thường**, vì `mV` và `MV` lệch chín bậc.
- **Bộ đọc và bộ ghi file section** — phân tích và sinh lại comment ID, phần front matter, dấu tham chiếu khối. Test quan trọng nhất của cả dự án nằm ở đây: **đọc rồi ghi lại phải ra đúng file ban đầu, từng byte**, thử trên hàng loạt đầu vào sinh tự động. Nếu vòng này không kín thì mọi lệnh ghi vào vault đều có nguy cơ làm hỏng file mà không ai biết.
- **Định nghĩa dữ liệu (schema)** cho phần front matter và các file máy đọc, để kiểm tra tự động thay vì tin vào quy ước.
- **Phần tính dẫn xuất** — đường dẫn, breadcrumb, thứ tự, số khối, số từ, danh sách tham chiếu ra. Đặt ở đây, **không đặt trong từng lệnh**: cả bộ chuyển đổi, lệnh định dạng và lệnh sinh index đều cần đúng logic này. Viết ba lần là ba lần lệch nhau — đúng cái nguyên tắc 6 cảnh báo.

**Chặn:** thất bại 1, 2, 3.
**Xong khi:** test đọc-ghi-lại kín trên đầu vào sinh tự động; ba hàm văn bản có test cho ký tự CJK, khoảng trắng đặc biệt, và ký tự độ rộng bằng không.

**Trạng thái: xong.** 283 test xanh. Vòng đọc-ghi kín trên đầu vào sinh tự động, và ví dụ mẫu trong đặc tả round-trip đúng từng byte. Ba lỗi thật mà việc implement làm lộ ra:

- **Bug đã được dự đoán, và nó có thật.** Quyết định 8c của F01 nói hàm đổi khối thành văn bản thuần phải bỏ escape Markdown. Lần viết đầu, biểu thức của tôi có `[]` trong character class nên class bị đóng sớm — `\|` không được bỏ escape. Test bắt được. Nếu không, mọi ô bảng chứa dấu `|` sẽ bị báo là mất nội dung.
- **Section front-matter `level: 0` không biểu diễn được.** §6.1 cho heading 1–6 dấu `#`, nên section đó ghi ra được mà đọc lại không được — và đó là section chứa lịch sử phiên bản. Đổi thành `level: 1`, và bộ ghi giờ **từ chối** ghi một khối heading không có dòng ATX thay vì ghi ra file không đọc lại được.
- **Quy tắc quote YAML phải tính đến cả hai phương ngữ.** `1e5` là chuỗi với bộ đọc YAML 1.1 và là số thực với bộ đọc YAML 1.2. Vault được Obsidian đọc, không chỉ `specctl` đọc.

Ba quyết định này ghi ở `G-data-contract.md`, quy tắc đã áp vào D v2.2.

### F04 · Bộ tài liệu thử

**Làm gì:** một tập file `.docx` nhỏ, mỗi file cô lập một ca khó, commit vào repo làm đầu vào test cho F05.

**Vì sao cần:** phần dễ mất dữ liệu nhất là bộ đọc OOXML (F05). Muốn chứng minh nó không mất dữ liệu thì phải có đầu vào chứa đúng các ca khó: một đoạn bị xoá theo track changes, một đoạn bọc trong content control, một bảng merge cell, một text box, một mục lục tự động, một công thức, một tham chiếu chéo. Không thể dùng file của customer làm test: file lớn, không cô lập được từng ca, và là nội dung hợp đồng.

**Nguồn:** **gõ tay trong Word rồi commit.** Đây là đường chính, và là đường đúng — Word sinh ra OOXML thật, đúng như file customer sẽ gửi. Owner làm một lần, và vì file đã commit nên nó cố định từng byte, test chạy lại luôn ra cùng kết quả. Một số ca như SmartArt hay OLE object thì chỉ Word làm được.

**Cộng thêm một helper sinh `.docx` bằng XML thuần** — nhỏ, không phải đường chính, phục vụ đúng hai việc mà Word không làm được:

| Việc | Vì sao Word không làm được |
|---|---|
| Ca **hỏng có chủ ý** — ví dụ một bảng không serialize được bằng cả hai dạng, để kiểm chứng đường hạ cấp ở F10 | Word luôn ghi ra OOXML hợp lệ. Không gõ tay được một file cố ý sai |
| Ca **hồi quy phát hiện về sau** — chạy trên tài liệu thật thấy một lỗi, cần viết ngay một ca tối thiểu tái hiện nó | Quay lại Word gõ từng ca mới là vòng lặp chậm, và ca đó thành file nhị phân không review được qua diff |
| **File thế chỗ** cho ba file Word chưa có, để nhóm B không bị chặn (thêm vào lúc implement — xem phần trạng thái) | Không phải Word không làm được, mà là chưa ai gõ. Đây là giải pháp tạm, không thay được đường chính |

**Chặn:** thất bại 1.
**Xong khi:** bảy ca kể trên có file tương ứng và bộ đọc chạy được trên tất cả; đường hạ cấp ở F10 có một ca hỏng có chủ ý để kiểm chứng.

**Trạng thái: xong, nhưng 3 file Word vẫn còn nợ.** 394 test xanh, 4 skip (381/17 khi không có pandoc) — sau khi merge với F05. Bảy ca khó đều có file chứa nó trên đĩa, và bộ đọc chạy được trên tất cả — đó là tiêu chí "xong khi" ở trên. Ca hỏng có chủ ý cho F10 đã commit.

**Cách giải quyết chỗ kẹt.** Đường chính vẫn là gõ tay trong Word, và không có gì thay được nó. Nhưng để F04 chặn cả nhóm B trong lúc chờ là trả giá quá đắt, nên mỗi file Word giờ có một **file thế chỗ** sinh từ OOXML thuần (`built_constructs.docx`, `built_revisions.docx`, `built_containers.docx`), commit vào repo. Ba điểm làm cho nó không biến thành cái cớ để không giao file thật:

- **Một danh sách yêu cầu, hai file.** File thế chỗ và file Word dùng chung đúng một danh sách trong `tests/support/fixtures.py` — nó không thể âm thầm bao phủ ít hơn phần file Word phải bao phủ. Có test kiểm chính điều đó.
- **File Word thắng ngay khi có.** `require("constructs.docx")` trả về file Word nếu nó tồn tại, không thì trả file thế chỗ. Giao file thật không phải sửa một dòng test nào.
- **Test vẫn báo còn nợ.** File thế chỗ không phải một lần giao hàng. `test_fixtures.py` vẫn liệt kê ba file Word còn thiếu mỗi lần chạy.

**Cái mà file sinh ra không chứng minh được — và một bug thật lộ ra từ đó.** File sinh chứng minh bộ đọc xử lý được một construct; nó **không** chứng minh construct đó đúng hình dạng Word ghi ra, vì `lxml` đọc được mọi XML hợp cú pháp. Đem hỏi một bộ đọc độc lập (pandoc) thì ra ngay: bộ sinh đang ghi track changes dưới dạng bọc cả `w:p` trong một `w:ins`. Dạng đó parse được, qua được kiểm tra `//w:ins`, và **bị pandoc bỏ im lặng** — trong khi Word ghi `w:ins` ở mức run, bên trong `w:p`, còn dấu kết đoạn được đánh dấu riêng ở `w:pPr/w:rPr`.

Nếu không bắt được, F05 sẽ được viết theo một hình dạng Word không bao giờ tạo ra: xanh hết trên fixture, và **mất đoạn văn được chèn** trên tài liệu customer. Đúng thất bại 1, đúng dạng im lặng nhất của nó. Đã sửa bộ sinh, thêm một yêu cầu bắt buộc về hình dạng run-level, và một test hỏi thẳng bộ đọc độc lập thay vì hỏi parser của chính mình.

**Sửa fixture xong thì lộ tiếp một bug trong F05.** Word ghi một đoạn được chèn bằng **hai** thẻ `w:ins` — một quanh các run, một trên dấu kết đoạn. Bộ đếm của W2 đang đếm cả hai, nên mọi đoạn văn người review gõ một lần sẽ được báo là hai lần chèn, và con số trong `coverage.json` mất ý nghĩa "tài liệu bẩn tới đâu". Đã sửa: đếm revision ở phần nội dung, còn revision trên dấu kết đoạn chỉ đếm khi trong đoạn đó không có revision cùng loại — vì một lần tách/gộp đoạn mà không đổi chữ vẫn là revision chưa giải quyết, không được im. Quy tắc ghi vào D §10.5.

Đây là lý lẽ cho cả F04: fixture đúng không phải để test xanh, mà để **bug xuất hiện sớm**. Hai bug trên đều là loại không có triệu chứng nào cho tới khi chạy trên tài liệu thật.

Phần đáng nêu tiếp theo: **nội dung file được kiểm tra, không phải chỉ tên file.** `tests/test_fixtures.py` đọc thẳng OOXML và báo đúng construct nào thiếu, vì Word thường không lưu đúng cái người viết nghĩ:

| Việc vô tình làm | Kết quả |
|---|---|
| Accept tracked changes trước khi lưu | Mất `w:del`. File mở vẫn bình thường và test không kiểm gì cả |
| Xoá hết nội dung trong content control | Word bỏ luôn thẻ `w:sdt` khi lưu |
| Dán mục lục dưới dạng text | Không có field code, nên không có gì để skip |
| Chèn ảnh bằng "link to file" | Không có phần ảnh nào trong package |

Mỗi trường hợp trên về sau sẽ hiện ra dưới dạng "bộ đọc làm mất chữ", và bộ đọc bị quy trách nhiệm cho một construct chưa từng có trong file. Kiểm tra đặt lỗi về đúng chỗ gây ra nó.

Cuối cùng: **file nhị phân commit vào repo là thứ không ai review được** — nên mọi file sinh ra đều phải tái tạo được. `python scripts/build_fixtures.py --check` so từng part của file đã commit với một lần build mới. Sửa tay một file `.docx` là thay đổi duy nhất mà không một diff nào cho thấy.

---

## Nhóm B — Chuyển đổi tin cậy

### F05 · Bộ đọc cấu trúc file Word

**Làm gì:** đi qua toàn bộ cây XML của tài liệu theo đúng thứ tự văn bản. Đây là **nơi duy nhất mà dữ liệu bị mất một cách im lặng**, nên nó được viết theo đệ quy và có bốn hành vi bắt buộc:

- **Đi xuyên qua** các thành phần bao bọc: content control, khối lựa chọn tương thích, smart tag. Chúng chỉ là bao bì; nội dung bên trong là nội dung thật.
- **Giữ** phần được chèn theo track changes (đó là trạng thái hiện hành), **bỏ** phần bị xoá theo track changes, và **đếm cả hai**. Một bộ đọc chỉ gom chữ sẽ phát ra đoạn văn đã bị xoá như thể là yêu cầu còn hiệu lực — đây chính là thất bại 1 ở dạng tệ nhất, vì nó tạo ra nội dung sai bằng cách đọc sai chứ không phải bằng cách bịa.
- **Bỏ có ghi nhận** mục lục tự động, header và footer — kèm số đoạn và số ký tự đã bỏ, để cái bỏ có chủ ý nằm cạnh cái đã lấy.
- **Gặp thành phần không nhận ra mà bên trong có nội dung thì vẫn phải đi xuống**, và ghi một dòng ghi chú. Không bao giờ bỏ qua.

**Chặn:** thất bại 1.
**Xong khi:** chạy đúng trên cả bảy ca của F04; ca track changes phát ra phần chèn, bỏ phần xoá, và đếm đúng cả hai.

**Trạng thái: xong phần code và test dựng bằng XML; 6 test chờ 3 file Word của F04.** 350 test xanh. Bộ đọc nằm ở `specctl/ingest/`: `package.py` (mở gói, trả về từng part) và `walk.py` (vòng đệ quy, W1–W6). Ra khỏi nó là một **luồng khối** — chưa phải Markdown. Quyết định bảng trình bày thế nào (F09), shape hạ cấp ra sao (F10), khối nào thuộc section nào (F07) đều đọc luồng này. Tách như vậy để câu hỏi "có mất gì không" trả lời được một mình: chữ đã vào luồng thì không giai đoạn nào sau đó làm mất nó mà không nêu lý do.

Điểm đáng ghi:

- **Test ở đây phần lớn là khẳng định phủ định.** "Phần chèn được phát ra" mới là nửa test; nửa còn lại là "phần xoá thì không", và nửa thứ ba là "cả hai đều được đếm" — vì nhìn từ ngoài, một lần bỏ im lặng và một lần bỏ có ghi nhận trông giống hệt nhau nếu không ai đếm.
- **Trạng thái field phải sống qua nhiều đoạn văn.** Một TOC mở ở đoạn này và đóng ở đoạn cách đó vài chục đoạn. Chỉ xét đoạn đang cầm thì giữ nguyên cả mục lục thành yêu cầu; quên pop thì **bỏ im lặng toàn bộ phần còn lại của tài liệu**. Có test cho cả hai chiều.
- **`TOCHeading` cố tình không bị bỏ.** Nó là style của chính dòng chữ "Table of Contents" — một heading tài liệu thật sự có. Lọc theo tiền tố `TOC` sẽ nuốt nó.
- **Chỉ mục đoạn văn được xây bằng `id()` của phần tử lxml, nên mọi phần tử đã đánh số đều được giữ sống.** lxml giải phóng proxy khi hết tham chiếu và cấp lại đúng địa chỉ đó cho proxy kế tiếp — một bản đồ theo `id()` sẽ bắt đầu trỏ sai đoạn, không báo gì. Cùng một cái bẫy đã có sẵn trong `tests/test_pandoc_oracle.py` và đã sửa luôn.
- **Đoạn bị bỏ vẫn tiêu thụ số thứ tự của nó.** Chỉ mục trỏ vào *bản gốc*; đánh số lại quanh chỗ đã bỏ làm mọi issue lệch đi một đoạn so với thứ nó nói tới.

Hai lỗi thật mà việc implement làm lộ ra, cả hai đều nằm ở **công cụ trọng tài**, không phải ở bộ đọc — ghi ở `G-data-contract.md` quyết định 15, quy tắc đã áp vào D v2.3:

- **Phép đo độ trung thực đếm một text box thành ba đoạn nguồn**, trong đó một đoạn là hai nhánh `mc:Choice` và `mc:Fallback` dính liền nhau — một chuỗi không tồn tại ở đâu trong tài liệu, nên không bộ ghi nào phát ra được và nó vĩnh viễn nằm trong danh sách "chưa bao phủ". ACC-2 tụt khoảng một đoạn cho mỗi text box. Đây là F1 ở chiều ngược lại: con số bị bóp xuống bởi chính cách đếm.
- **Test oracle so với pandoc không lọc mục lục**, trong khi §10.12 F2 nói mục lục ngoài phạm vi và §10.5 W4 bỏ nó có ghi nhận. Pandoc phát ra dòng mục lục như đoạn văn thường, nên khi `containers.docx` có mặt, test sẽ báo bộ đọc của ta "làm mất" đúng những dòng đặc tả bảo phải bỏ. Đã kiểm chứng bằng ba file dựng thay cho ba file Word chưa có: sau khi sửa, độ bao phủ 1.0000 trên cả ba và oracle không tìm ra đoạn nào pandoc lấy được mà ta không.

**Nghiệm thu:** các ca khó hiện chạy trên `built_*.docx` (stand-in dựng bằng XML, xem F04), nên nhóm B không bị chặn. Nhưng **stand-in không ký được F05**: nó là OOXML hợp lệ mà lxml chấp nhận, còn tài liệu customer thì do Word ghi, và đúng chỗ khác nhau giữa hai thứ đó là chỗ một bộ đọc mất nội dung mà không nói gì. `resolve()` tự chuyển sang file Word ngay khi có, không đổi một dòng test nào.

Ba file Word đó là **nội dung hợp đồng và không vào repo**: `.gitignore` chặn đúng ba tên (không dùng wildcard — `built_*.docx` và `degraded.docx` là file dựng, không có nội dung customer, và được commit có chủ ý), còn `tests/fixtures/manifest.json` giữ SHA-256 thay cho chúng. Đổi lại, CI chỉ chạy được stand-in — cổng thật là máy của owner. Manifest bù đúng một lỗ hổng, và là lỗ hổng nguy hiểm nhất của cách làm đó: mở file ra lưu lại trong Word thì mọi test vẫn xanh nhưng đầu vào đã là tài liệu khác, và chữ "đã verify" lặng lẽ trỏ sang chỗ chưa ai kiểm.

Quy trình đóng F05 là **bốn bước ở `H-testing.md` §8**, không phải một lần chạy `pytest`: bộ test xanh nói bộ đọc làm đúng những gì test yêu cầu, không nói test đã yêu cầu hết những gì có trong file — mà điều F05 khẳng định lại là một mệnh đề phủ định. `scripts/verify_f05.py` là cổng của quy trình đó; nó in ra bằng chứng đúng hình dạng của lời khẳng định (từng construct, từng bộ đếm, từng đoạn chưa bao phủ kèm vị trí, và so với pandoc), chỉ đọc, và đã được kiểm chứng là **biết báo đỏ** trên năm đường hỏng: fixture bị accept track changes trước khi lưu, byte lệch manifest, file thiếu, `--record` trên lần chạy đỏ, và đang đọc stand-in thay vì file Word. Trạng thái đã ký là trạng thái **duy nhất không còn skip nào**: `399 passed, 0 skipped`.

### F06 · Đánh số mục và số danh sách

**Làm gì:** tính lại số mục ("3.2") và số thứ tự danh sách từ định nghĩa đánh số của Word, bằng cách duy trì bộ đếm theo từng cấp.

**Vì sao cần:** số mục **không nằm trong phần chữ** của file Word — Word tự sinh ra lúc hiển thị. Không tính lại thì mất toàn bộ cấu trúc phân cấp của tài liệu, và mất luôn cách người ta gọi tên một mục trong đời thực.

Không tính được thì để trống, phát ra phần chữ nguyên vẹn, và đếm vào báo cáo. Không bao giờ để lỗi đánh số làm chết cả lần chuyển đổi.

**Chặn:** thất bại 2.
**Xong khi:** số mục khớp với những gì mở file trong Word thấy, trên toàn bộ tài liệu thật.

### F07 · Chia file theo section

**Làm gì:** mỗi heading ở cấp nông hơn một ngưỡng cấu hình được thì bắt đầu một file mới, đặt tên theo ID của chính heading đó. Heading sâu hơn ngưỡng thì nằm trong file như một khối bình thường.

Riêng phần nội dung nằm **trước heading đầu tiên** — trang bìa, bảng kiểm soát tài liệu, phạm vi, và đặc biệt là **lịch sử phiên bản** — được gom vào một section riêng. Một spec theo ASPICE luôn có lịch sử phiên bản trước heading đầu tiên, đó là nội dung hợp đồng, và không có quy tắc này thì nó không có chỗ nào để nằm, tức là bị mất.

**Chặn:** thất bại 1, 2.
**Xong khi:** nội dung trước heading đầu tiên có file của nó; số file khớp số heading ở cấp tương ứng.

### F08 · Cấp ID và sổ đăng ký

**Làm gì:** cấp ID tuần tự theo thứ tự tài liệu, và ghi một sổ đăng ký máy đọc được, lưu cho mỗi ID: trạng thái, kiểu khối, section chứa nó, và một mã băm nội dung.

Sổ này là nơi lịch sử được giữ. Một ID không bao giờ bị xoá khỏi sổ — khối bị xoá hay bị gộp thì chuyển sang trạng thái kết thúc, kèm thông tin nội dung đã đi đâu. Bộ đếm ID chỉ tăng, không bao giờ giảm hay đặt lại.

**Chặn:** thất bại 2, 4.
**Xong khi:** mọi khối có ID hợp lệ và duy nhất; sổ ghi ra ổn định từng byte khi chạy lại.

### F09 · Bảng

**Làm gì:** bảng đơn giản thành bảng Markdown dạng pipe; bảng có merge cell, có nội dung nhiều tầng trong ô, hay có bảng lồng thì thành HTML `<table>` với `rowspan`/`colspan`.

**Vì sao cần cả hai đường:** spec automotive có rất nhiều bảng merge cell. Ép chúng thành bảng pipe là mất cấu trúc — mà cấu trúc của bảng chính là nội dung của nó.

**Chặn:** thất bại 1.
**Xong khi:** trên tài liệu thật, tỉ lệ bảng giữ được ở một trong hai dạng đạt ngưỡng đã thoả thuận, phần còn lại được liệt kê từng cái.

### F10 · Hạ cấp thay vì bỏ

**Làm gì:** hiện thực nguyên tắc ở mục 4.2. Thứ gì không biểu diễn được thì thành một khối `raw` bị khoá, mang phần chữ trích được, kèm XML gốc lưu ra file riêng, kèm ghi chú nêu lý do. Báo cáo đếm nó là "giữ được ở dạng hạ cấp" — không bao giờ tính là giữ nguyên, cũng không bao giờ tính là đã bỏ.

**Chặn:** thất bại 1.
**Xong khi:** một bảng cố ý làm hỏng vẫn ra một khối có ID, có XML gốc bên cạnh, có ghi chú lỗi, và phần chữ trong bảng đó vẫn được tính là đã bao phủ.

### F11 · Đo độ trung thực, báo cáo và cửa chặn

**Làm gì:** hiện thực phép đo ở mục 4.3, sinh một báo cáo máy đọc được và một bản cho người đọc, rồi đặt **cửa chặn**: ba ngưỡng (độ bao phủ chữ, tỉ lệ bảng giữ được, tỉ lệ tham chiếu giải được). Không đạt ngưỡng thì lệnh thoát với mã lỗi, nêu tên cửa bị chặn, và **không để lại một vault nửa vời** — xây ở thư mục tạm rồi mới chuyển vào chỗ thật.

Đây là tính năng biến câu "chắc là đủ" thành một con số, kèm danh sách từng chỗ còn thiếu.

**Chặn:** thất bại 1.
**Xong khi:** có con số trên tài liệu thật; mọi đoạn chưa bao phủ được liệt kê kèm vị trí, số ký tự và lý do; vi phạm cửa chặn thì không sinh ra vault.

> **Điểm quyết định:** F11 là chỗ đầu tiên biết được Markdown có đủ làm bản gốc hay không. Nếu độ bao phủ hoặc tỉ lệ bảng không đạt, phải **dừng lại xem lại quyết định ở mục 5** trước khi làm tiếp — chứ không phải nới ngưỡng cho qua.

### F12 · Tham chiếu chéo thành liên kết sống

**Làm gì:** đọc bookmark, hyperlink nội bộ và trường REF trực tiếp từ XML, rồi phát ra liên kết dạng wikilink trỏ tới đúng ID.

**Vì sao cần:** tham chiếu chéo là cách spec tự nối các phần với nhau. Các công cụ chuyển đổi thông thường làm mất chúng, và khi đó agent không đi theo được chỉ dẫn "xem mục 5.1" — nó phải đoán, tức là quay lại thất bại 1 ở dạng khác. Đây cũng là dữ liệu duy nhất đủ tin để trả lời "sửa chỗ này thì ảnh hưởng chỗ nào".

Không giải được đích thì phát ra chữ thuần kèm ghi chú — không bao giờ tạo ra một liên kết chết mà vẫn đếm là thành công.

**Chặn:** thất bại 2.
**Xong khi:** mọi liên kết nội bộ hoặc trỏ tới đích tồn tại thật, hoặc xuất hiện trong danh sách ghi chú. Không có trường hợp thứ ba.

---

## Nhóm C — Agent đọc được

### F13 · Bản đồ tài liệu

**Làm gì:** sinh một file mục lục nhỏ: danh sách phân cấp mọi section kèm số mục, tiêu đề, liên kết, ID, số khối, số từ.

**Vì sao cần:** đây là bản đồ của agent. Đọc một file nhỏ để biết cần mở section nào, thay vì đọc cả vault rồi vẫn trả lời chung chung. File này phải nhỏ — vượt ngưỡng thì cảnh báo chia section sâu hơn.

**Chặn:** thất bại 2.
**Xong khi:** mọi section xuất hiện đúng một lần, mọi liên kết trong đó giải được; chạy lại không đổi gì.

### F14 · Lệnh định dạng

**Làm gì:** một lệnh sở hữu **toàn bộ** phần dẫn xuất: tính lại đường dẫn, breadcrumb, thứ tự, số khối, số từ, danh sách tham chiếu ra; thêm và bỏ dấu tham chiếu khối; chuẩn hoá thứ tự thuộc tính và định dạng file.

**Vì sao cần (nguyên tắc 6):** agent điều hướng bằng breadcrumb. Để nó sửa tay thì breadcrumb sẽ lệch, và agent đi sai mà không có một cảnh báo nào. Một lệnh sở hữu tất cả, người và agent chỉ sửa phần nội dung.

Lệnh này phải chạy **trước** lệnh kiểm tra, để việc lệch phần dẫn xuất không hiện ra như một phát hiện về nội dung. Nó phải làm hai pha — pha một quét cả vault thu tập đích liên kết, pha hai mới ghi — vì dấu tham chiếu của một khối phụ thuộc vào liên kết trong file khác.

**Chặn:** thất bại 2.
**Xong khi:** đổi tên một heading thì breadcrumb của nó và của mọi section con được tính lại đúng; chạy hai lần thì lần hai không đổi gì.

### F15 · Quy ước và kỹ năng cho agent đọc

**Làm gì:** một file quy ước ở gốc repo nêu rõ các điều agent phải làm và không được làm, cùng ba kỹ năng: cách điều hướng, cách đọc một section kèm các tham chiếu vào và ra, và giao thức hỏi-đáp.

**Vì sao cần:** không quy định rõ thì agent sẽ trả lời mà không trích dẫn ID — nghĩa là câu trả lời không kiểm chứng được, và đó là toàn bộ giá trị của việc 1. Danh sách "không được làm" cũng quan trọng ngang: không sửa khối bị khoá, không đổi ID, không sửa tay phần dẫn xuất, không đổi số hay đơn vị.

**Chặn:** thất bại 2, 3.
**Xong khi:** agent trả lời được mười câu hỏi thử, mỗi câu có trích dẫn ID chỉ đúng chỗ.

> **Điều kiện trước khi làm F15:** cần có xác nhận của customer về việc đưa nội dung spec qua model chạy trên cloud, ghi lại thành văn bản. Chưa có thì không mở phiên agent nào trên nội dung thật. Đây là việc rẻ nhất trong danh sách và chặn sớm nhất.

---

## Nhóm D — Kiểm soát ghi

> Nhóm này không tạo ra tính năng nào người dùng thấy được. Nó là điều kiện để nhóm E được phép tồn tại.

### F16 · So sánh số và đơn vị

**Làm gì:** hiện thực phép so ở mục 4.4. Bóc mọi con số kèm đơn vị trong một khối thành túi giá trị, so túi trước với túi sau, báo phần chênh. So sánh đơn vị phân biệt chữ hoa chữ thường.

Loại trừ những thứ không phải số đo: mã ID khối, phần bên trong liên kết, số mục trên dòng heading, số tham chiếu dạng "Figure 3-2", và nội dung trong khối code.

Báo cáo dạng `"50 ms" -> "80 ms"` chỉ khi thay thế một-đổi-một rõ ràng; mọi trường hợp khác in cả hai danh sách, vì một mũi tên sai chỗ còn tệ hơn không có mũi tên.

**Vì sao đây là tính năng quan trọng nhất của nhóm:** nó là tuyến phòng thủ duy nhất chống thất bại 3. Người review một diff dài sẽ không thấy `50` thành `80`. Máy thì luôn thấy.

**Chặn:** thất bại 3.
**Xong khi:** đổi một số thì bắt được; **đảo thứ tự câu mà không đổi số thì không báo gì** (phần thứ hai quan trọng ngang phần thứ nhất — một công cụ báo nhầm liên tục sẽ bị bỏ qua, và khi đó nó vô dụng).

### F17 · Khoá khối không review được

**Làm gì:** hình ảnh, shape, công thức dạng ảnh và khối hạ cấp bị đánh dấu khoá. Sửa vào là báo lỗi.

**Vì sao cần:** những khối này không review được bằng mắt qua diff văn bản. Một caption hình bị đổi nhìn hệt như không đổi.

**Chặn:** thất bại 3.
**Xong khi:** sửa caption của một hình bị khoá thì báo lỗi.

### F18 · Kiểm tra toàn vẹn địa chỉ

**Làm gì:** ID trùng, comment ID sai cú pháp hoặc sai thuộc tính so với kiểu khối, front matter sai định nghĩa, liên kết trỏ tới đích không tồn tại, file tham chiếu tới ảnh không có trên đĩa, khối chưa có ID.

**Vì sao cần:** ID trùng, comment hỏng hay liên kết chết làm vỡ toàn bộ hệ địa chỉ — tức là làm sụp nền móng ở mục 4.1. Mỗi kiểm tra ở đây đều rẻ, và phần "ảnh không có trên đĩa" chặn thất bại 1 trực tiếp: file mất thì nội dung mất thật, không có lệnh định dạng nào sửa được.

**Chặn:** thất bại 1, 2.
**Xong khi:** mỗi loại vi phạm có một ca thử làm nó phát và một ca thử không làm nó phát.

### F19 · Theo dõi nội dung đi đâu

**Làm gì:** hiện thực nguyên tắc ở mục 4.5. Phát hiện ID có trong bản đối chiếu mà biến mất khỏi bản làm việc; nếu có khai báo nguồn gốc thì chấp nhận, không có thì báo lỗi. Kiểm tra khai báo không trỏ tới ID lạ, và một ID không bị hai khối cùng khai là đã gộp.

**Vì sao cần:** không có nó thì cách duy nhất để gộp hai đoạn văn là tắt hẳn bảo vệ chống xoá cho cả lần chạy — bao gồm tắt luôn việc phát hiện những lần xoá do nhầm. Và không có nó thì mọi việc sắp xếp lại cấu trúc đều trông như xoá nội dung, cả với công cụ lẫn với customer đọc file Excel.

**Chặn:** thất bại 3, 4.
**Xong khi:** một lần gộp có khai báo thì qua; cùng lần gộp đó không khai thì báo lỗi; khai sai đích thì báo lỗi.

### F20 · So với đúng bản đối chiếu

**Làm gì:** mặc định so bản làm việc với **điểm mà nhánh hiện tại tách ra** khỏi nhánh chính, không so với commit cuối.

**Vì sao cần:** nếu mặc định so với commit cuối thì sau khi agent commit trên nhánh sửa, công cụ đang so bản sửa với chính bản sửa đó, và báo "sạch". Mọi kiểm tra ở F16 đến F19 im lặng cùng lúc, và đúng vào lúc cần chúng nhất. Một lỗi mặc định làm vô hiệu cả nhóm D.

**Chặn:** thất bại 3.
**Xong khi:** trên một nhánh đã có commit, lệnh kiểm tra chạy không tham số vẫn báo ra các thay đổi.

### F21 · Cấp ID cho khối mới, và cập nhật sổ

**Làm gì:** hai việc, tách riêng vì hai bản chất khác nhau:

- Cấp ID cho khối agent mới viết — chỉ thêm ID vào khối chưa có, giữ nguyên mọi byte khác.
- Cập nhật sổ đăng ký (trạng thái, nội dung đã đi đâu) bằng **một lệnh riêng chạy sau khi commit** — vì công cụ kiểm tra chỉ được đọc (nguyên tắc 7).

**Chặn:** thất bại 2, 4.
**Xong khi:** chỉ khối chưa có ID được thêm ID, mọi byte khác không đổi; lệnh kiểm tra không ghi một file nào.

---

## Nhóm E — Agent sửa được

### F22 · Luồng sửa có kiểm soát

**Làm gì:** cố định trình tự và ai làm bước nào: tạo nhánh → agent sửa **một** file section → định dạng → kiểm tra → **agent báo cáo nguyên văn kết quả kiểm tra** → người xem diff → sinh lại bản đồ → người commit → ghi log thành commit riêng → merge giữ nguyên lịch sử.

Bốn quy tắc: một phiên sửa một file (để diff review được); agent không commit; agent báo cáo nguyên văn, không được tóm gọn hay làm nhẹ phát hiện nào; định dạng chạy trước kiểm tra.

**Vì sao "báo cáo nguyên văn" là một quy tắc riêng:** một agent tóm gọn kết quả kiểm tra sẽ vô tình làm mất đúng dòng quan trọng nhất. Người review cần thấy cái máy thấy, không phải bản diễn giải của agent.

**Chặn:** thất bại 3, 4.
**Xong khi:** một section đi hết luồng, diff được review và merge, và lịch sử giữ đủ mã commit.

### F23 · Kỹ năng sửa spec

**Làm gì:** hai kỹ năng — sắp xếp lại một section theo cấu trúc mục tiêu đã thoả thuận, và chuẩn hoá cách trình bày mà không đổi nghĩa — cộng với thủ tục khai báo nguồn gốc khi tách hoặc gộp.

**Chặn:** đây là mục đích của việc 2.
**Xong khi:** ba đến năm section được cải thiện, đi hết luồng F22.

> **Điều kiện trước khi làm F23:** cần một bản mô tả cấu trúc mục tiêu, kèm **một ví dụ trước/sau lấy từ tài liệu thật**. Không có ví dụ thật thì không viết được kỹ năng này — "sắp xếp cho tốt hơn" không phải một chỉ dẫn thực thi được.

---

## Nhóm F — Giao hàng

### F24 · Sổ lý do thay đổi

**Làm gì:** một file chỉ ghi thêm, mỗi dòng một lần sửa: thời điểm, mã commit, section, kỹ năng đã dùng, lý do, số khối đổi, tóm tắt thay đổi về số.

**Vì sao cần:** đây là **nguồn duy nhất** cho cột "vì sao" trong file Excel giao customer. Không có nó thì câu hỏi ở thất bại 4 chỉ trả lời được hai phần ba: đổi cái gì, so với bản nào — nhưng không trả lời được vì sao.

**Chặn:** thất bại 4.
**Xong khi:** mỗi lần sửa có một dòng; file không bao giờ bị sinh lại đè mất.

### F25 · Xuất Excel

**Làm gì:** một sheet liệt kê mọi khối kèm ID, số mục, breadcrumb, kiểu, nội dung; một sheet chỉ chứa phần đã đổi, kèm phân loại (giữ nguyên / sửa / thêm / xoá / đã gộp / đã tách), nội dung cũ, lý do, mã commit, và cột thay đổi về số.

Hai điểm then chốt: phân loại **theo ID và theo khai báo nguồn gốc, không theo vị trí** — nên di chuyển một khối không bị báo là xoá rồi thêm lại. Và cột thay đổi về số **dùng lại đúng bộ so của F16** — một cách tính, hai nơi dùng, không bao giờ lệch nhau.

**Chặn:** thất bại 4.
**Xong khi:** xuất tại đúng mốc đối chiếu thì mọi dòng là "giữ nguyên"; sau một lần sửa đã biết trước thì đúng khối đó là "sửa", với nội dung cũ và mới đúng.

---

## Nhóm G — Nên có

Hoãn được. Không cái nào chặn ai.

| # | Tính năng | Vì sao hoãn được |
|---|---|---|
| **F26** | Danh sách tham chiếu vào từng khối | Tìm bằng công cụ grep theo ID cũng ra được kết quả tương đương |
| **F27** | Vẽ lại shape và SmartArt thành ảnh | Đã có đường hạ cấp nên **không mất dữ liệu**, chỉ thiếu hình minh hoạ. Khuyến nghị giữ ưu tiên thấp: cách làm phải dựa vào giả định "công cụ ngoài phát ra đúng một ảnh cho mỗi đối tượng, theo đúng thứ tự" — một giả định về hành vi, không phải một hợp đồng |
| **F28** | Công thức toán thành LaTeX | Đã có phương án dự phòng bằng ảnh. Thêm nữa: cách làm trong đặc tả dựa vào một stylesheet là tài sản của Microsoft — đóng gói nó vào sản phẩm giao customer là rủi ro pháp lý thật. Nếu làm thì viết bộ chuyển đổi riêng cho tập con thường dùng |
| **F29** | Các kiểm tra còn lại + hook trước commit | Phần lớn đã được lệnh định dạng tự sửa, hoặc chỉ ở mức cảnh báo. Hook là một lớp an toàn thêm, luồng thủ công vẫn đủ |
| **F30** | Bộ câu hỏi chuẩn để đo chất lượng | Dùng để **đo** chất lượng trả lời, không cần để hệ thống chạy. Nên làm khi cần con số báo cáo |

---

## Nhóm H — Hoãn có chủ ý

### F31 · Đọc lại từ bản .docx mới

**Trạng thái: không làm trong giai đoạn này.**

Chỉ cần khi customer gửi một bản Word mới. Nhưng một khi vault đã là bản gốc để làm việc, việc đọc lại từ file Word sẽ **ghi đè toàn bộ công sức của việc 2**. Đặc tả hiện tại chưa giải quyết bài toán hợp nhất giữa bản Word mới và các thay đổi đã làm trong vault.

Làm tính năng này trước khi có thiết kế hợp nhất là xây một cái nút xoá việc đã làm. Hoãn đến khi có nhu cầu thật **và** có thiết kế luồng hợp nhất.

---

# Phần IV — Phạm vi và đầu vào

## 8. Không làm trong giai đoạn này

Không phải vì khó, mà vì chưa đo được cái đau. Mọi đề nghị thuộc danh sách này đi vào `B-limitations-roadmap.md`, không đi vào giai đoạn này.

Không dựng server trung gian cho agent. Không database, không index tìm kiếm. Không giao diện web. Không xử lý nhiều tài liệu cùng lúc. Không hỗ trợ tiếng Nhật. Không ghi ngược lại ra file Word. Không chạy model cục bộ. Không chatbot. Không các tính năng quản lý yêu cầu (luồng phê duyệt, ma trận truy vết). Không phân tích ảnh hưởng quá một bước. Không sửa đồng thời nhiều người — một người, một nhánh, git là cơ chế duy nhất.

## 9. Cần từ owner

Ba thứ không phải implementer quyết được:

| Cần gì | Chặn tính năng nào | Nếu chậm thì sao |
|---|---|---|
| **File Word thật** đặt vào repo | F11, và mọi con số về sau | Chỉ đo được trên tài liệu thử. Nhóm A vẫn làm được bình thường |
| **Bộ file `.docx` test** gõ tay trong Word, mỗi file một ca khó (xem F04) | Không còn chặn F05, nhưng vẫn cần | Đã có file thế chỗ sinh từ OOXML thuần nên nhóm B làm được. Cái còn thiếu là bằng chứng bộ đọc chạy đúng trên OOXML **Word thật sự ghi ra** — và một số ca (SmartArt, OLE object, content control thật) chỉ Word tạo được. Việc chỉ làm một lần, nên làm sớm |
| **Xác nhận của customer** về việc đưa nội dung spec qua model trên cloud, ghi thành văn bản | F15 | Rẻ nhất để có, chặn sớm nhất. Chưa có thì không mở phiên agent nào trên nội dung thật |
| **Ngưỡng độ trung thực** được thoả thuận | F11 | Phép đo chạy được nhưng không có mốc để kết luận đạt hay không |
| **Cấu trúc mục tiêu** kèm một ví dụ trước/sau thật | F23 | Không viết được kỹ năng sắp xếp lại. Đến nhóm E mới cần, nên còn thời gian |

## 10. Tài liệu

| File | Trạng thái | Dùng để |
|---|---|---|
| `F-features.md` | **Đang hiệu lực** | Tài liệu này. Vấn đề, phương pháp, thứ tự tính năng. Đọc trước |
| `D-implementation-spec.md` | **Đang hiệu lực** | Đặc tả kỹ thuật chi tiết, v2.1. Tra khi cần biết một quy tắc chính xác ra sao. Đọc sau khi đã hiểu tài liệu này |
| `G-data-contract.md` | Tham khảo | Tám quyết định của F01 và lý do từng cái. Không chuẩn — quy tắc nằm trong D. Tra khi muốn biết "vì sao quy tắc này lại thế" |
| `B-limitations-roadmap.md` | **Đang hiệu lực** | Cái gì cố tình bỏ, và khi nào thì nên đầu tư thêm. Dành cho owner và stakeholder |
| `archive/` | Lịch sử | Bản giao đầu tiên, danh sách rà soát nó, và bản review dẫn tới tài liệu này. Giữ để tra nguồn gốc quyết định, **không implement từ đó** |
