# Hạn chế và lộ trình mở rộng

**Phiên bản:** 1.0 · **Ngày:** 2026-09-20
**Đi kèm:** `F-features.md` (vấn đề, phương pháp, thứ tự tính năng) và `D-implementation-spec.md` (chi tiết kỹ thuật)
**Người đọc:** owner và stakeholder. Dùng để quyết định *khi nào* đầu tư thêm, và *đầu tư vào đâu*.

---

## 1. Mục đích

Bản tạm thời (3 tuần) cố tình bỏ nhiều thứ. Tài liệu này trả lời ba câu hỏi:

1. **Bỏ những gì, và điều đó gây ra hậu quả gì?**
2. **Sống chung với nó như thế nào trong lúc chưa làm?**
3. **Khi nào thì nên làm tiếp, và làm cái gì?**

Nguyên tắc xuyên suốt: **không xây trước khi thấy đau.** Mỗi hạng mục dưới đây có một **điều kiện kích hoạt** cụ thể, quan sát được, chứ không phải cảm tính.

## 2. Vì sao có thể hoãn mà không phải làm lại

Bản tạm thời đặt cược vào đúng một thứ: **mỗi block có một ID bất biến, nằm ngay trong file Markdown.**

Vì ID nằm trong dữ liệu, nên mọi thứ về sau đều **cộng thêm được**:

| Muốn thêm                                      | Lấy dữ liệu từ đâu                      | Có phải sửa dữ liệu cũ không              |
| ------------------------------------------------ | --------------------------------------------- | ------------------------------------------------ |
| Index tìm kiếm (từ khóa, vector)             | Quét vault                                   | Không                                           |
| Graph quan hệ có kiểu                         | Quét wikilink và anchor                     | Không                                           |
| MCP server                                       | Bọc CLI sẵn có                             | Không                                           |
| Chatbot RAG                                      | Chunk theo section, đã có breadcrumb       | Không                                           |
| Nhiều file                                      | ID đã có tiền tố theo document           | Không                                           |
| Store JSON (nếu cần độ trung thực cao hơn) | Parse lại vault, hoặc ingest lại từ .docx | Có, nhưng ID được giữ qua`meta/ids.json` |

Đây là lý do kiến trúc "đơn giản" này không phải là nợ kỹ thuật, mà là **một bước đi đúng thứ tự**.

## 3. Bảng tổng hợp hạn chế

| #   | Hạn chế                                               | Tác động                                                                                | Sống chung ra sao                                        | Giải pháp dài hạn                                                                   | **Kích hoạt khi**                                   | Công sức |
| --- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ---------- |
| L1  | Bảng phức tạp và shape chỉ giữ được một phần | Một số nội dung ở dạng HTML hoặc ảnh, agent khó sửa                               | Đánh dấu`locked`, liệt kê trong coverage, sửa tay | Store JSON canonical cho bảng, hoặc trích qua Word                                   | Coverage bảng < 90%, hoặc cần sửa bảng thường xuyên | 1–2 tuần |
| L2  | Hình và shape agent không "hiểu"                    | Câu hỏi liên quan tới sơ đồ trả lời kém                                          | Giữ caption, tự viết mô tả khi cần                  | LLM vision sinh mô tả, lưu cạnh hình                                               | ≥ 20% câu hỏi golden set liên quan tới hình bị sai   | 2–3 ngày |
| L3  | Không có graph có kiểu, không có tool impact      | Không trả lời tự động được "sửa chỗ này ảnh hưởng tới đâu" nhiều bước | `backlinks.md` và grep theo ID (1 bước)              | Bảng`edges` trong SQLite, tool `neighbors`, `impact`                             | Cần đi ≥ 2 bước, hoặc backlink bắt đầu bỏ sót    | 1 tuần    |
| L4  | Không có tìm kiếm ngữ nghĩa                       | Câu hỏi diễn đạt khác từ trong spec thì tìm không ra                             | `index.md` + grep + agent đọc theo section            | FTS5 + sqlite-vec, hybrid search                                                        | ≥ 20% câu hỏi không tìm được bằng từ khóa        | 1 tuần    |
| L5  | Không có MCP server                                   | Chỉ dùng được với harness có quyền đọc file (Claude Code)                        | Dùng Claude Code                                         | `spec-mcp` bọc CLI, thêm `read`, `search`, `context`, `neighbors`           | Cần LLM local, Claude Desktop, hoặc người khác dùng   | 3–5 ngày |
| L6  | Một file, không có corpus                            | Không trả lời được câu hỏi xuyên tài liệu                                       | Ngoài phạm vi pilot                                     | Registry tài liệu, ID theo document (đã sẵn), extractor plugin cho quan hệ domain | Khi spec thứ hai được đưa vào                        | 1–2 tuần |
| L7  | Quan hệ qua Input và signal chưa được trích      | Không biết input đến từ đâu                                                         | Đọc bằng mắt                                          | Extractor plugin:`consumes`, `produces`, `depends_on` kèm độ tin cậy          | Cùng lúc với L6                                          | 1 tuần    |
| L8  | Chỉ tiếng Anh                                         | Chưa làm việc trên bản gốc tiếng Nhật                                              | Dùng bản dịch đã thống nhất với khách hàng      | Tokenizer tiếng Nhật, embedding đa ngôn ngữ, ghép EN và JP theo cấu trúc       | Khi khách hàng yêu cầu làm trên bản gốc             | 2 tuần    |
| L9  | Không có chatbot và eval tự động                  | Đo chất lượng bằng tay                                                                | Golden set chạy thủ công                               | `ask` (RAG có trích dẫn), `eval` so sánh A/B theo baseline                      | Khi cần chứng minh cải tiến ở quy mô lớn             | 1–2 tuần |
| L10 | Không ghi ngược ra Word                              | Bàn giao bằng Excel                                                                      | Đầu ra hiện tại là Excel                             | Exporter DOCX theo template, hoặc ReqIF                                                | Khi khách hàng yêu cầu bản Word                        | 1–2 tuần |
| L11 | Chưa thử LLM local                                    | Phụ thuộc Claude                                                                         | Dùng Claude                                              | Chạy lại cùng skill với Ollama (qua MCP ở L5)                                      | Khi có ràng buộc chi phí hoặc bảo mật                | 3–5 ngày |
| L12 | Chỉ một người dùng, cần VS Code và Git           | Team chưa dùng được                                                                   | Owner dùng, người khác xem Obsidian hoặc Excel       | Web UI đọc và duyệt, gọi cùng CLI hoặc MCP                                       | Khi có người thứ ba tham gia đều đặn                | 2–4 tuần |
| L13 | Không có kiểm tra tự động khi commit              | Phụ thuộc người nhớ chạy validate                                                    | Ghi trong`CLAUDE.md`                                    | Git hook hoặc CI chạy`specctl validate` và `index`                               | Khi có commit lọt lỗi                                    | 1 ngày    |
| L14 | Chưa có backup ngoài git local                       | Rủi ro mất máy                                                                          | Đẩy lên git server nội bộ                            | Quy trình backup, mirror                                                               | Ngay khi có dữ liệu thật đáng giá                    | 0,5 ngày  |

## 4. Chi tiết theo nhóm

### 4.1 Độ trung thực khi ingest (L1, L2)

**Bản chất:** Markdown là định dạng trình bày tuyến tính. Bảng có merged cell, shape, SmartArt, công thức không có cách biểu diễn tự nhiên.

**Bản tạm thời xử lý:** bảng phức tạp dùng HTML, shape render thành ảnh kèm OOXML gốc, block đánh dấu `locked`, mọi thứ không xử lý được đều nằm trong coverage report.

**Giải pháp dài hạn, theo thứ tự tăng dần:**

1. Mở rộng biểu diễn HTML cho bảng (rẻ).
2. LLM vision sinh mô tả cho hình và shape, lưu thành block `description` cạnh hình (giúp cả agent lẫn RAG).
3. **Store JSON canonical** cho toàn bộ nội dung, Markdown lùi về vai trò bản chiếu cho người đọc. Đây là thay đổi lớn nhất trong toàn bộ lộ trình, nhưng ID được giữ qua `meta/ids.json` nên không mất lịch sử.
4. Trích qua chính Word (COM/Office JS) nếu cần độ trung thực tuyệt đối.

**Đừng làm bước 3 sớm.** Chỉ làm khi số liệu coverage chứng minh là cần.

### 4.2 Truy vấn và tri thức (L3, L4)

**Bản chất:** hiện tại agent định vị bằng `index.md` và grep. Cách này chính xác nhưng chỉ đi được một bước và chỉ khớp từ khóa.

**Lộ trình:**

1. **SQLite index dựng từ vault** (1 file, dựng lại được): bảng `blocks`, `sections`, `edges`, cộng FTS5 cho BM25.
2. **Cạnh có kiểu và độ tin cậy**: `word_link` (tất định), `text_ref` (suy ra từ câu chữ), `similar_to` (embedding, chỉ gợi ý).
3. **Vector search** qua `sqlite-vec`, embedding theo section có breadcrumb ở đầu.
4. **Context pack tính sẵn** cho mỗi section, để agent lấy đủ ngữ cảnh trong một lần gọi. Đây là thứ giúp nhiều nhất cho model nhỏ.
5. **Tool `impact`**: duyệt ngược nhiều bước, xếp hạng theo độ tin cậy.

Toàn bộ nhóm này **đọc vault, không sửa vault**, nên có thể làm song song với việc dùng hằng ngày.

### 4.3 Lớp truy cập (L5)

Khi cần dùng harness khác hoặc LLM local, bọc CLI thành **spec-mcp** với các tool: `outline`, `read`, `search`, `context`, `neighbors`, `impact`, `checkout`, `commit`, `export`, `lint`.

Lưu ý thiết kế: **`commit` là tool ghi duy nhất**, và nó tự đọc file trên đĩa chứ không nhận nội dung do LLM truyền vào. Đây là điều kiện để không bị sửa lén.

### 4.4 Nhiều file và quan hệ xuyên file (L6, L7)

**Đã chuẩn bị sẵn:** ID có tiền tố document (`SYS-000120`), thư mục vault theo document, wikilink dùng ID nên xuyên file được ngay.

**Cần thêm:** registry tài liệu, và plugin trích quan hệ domain. Với spec kiểu function có section Input và Output, quan hệ `consumes`, `produces`, `depends_on` có thể suy ra qua tên signal. Cần kèm độ tin cậy và một báo cáo "signal không tìm thấy nguồn" — bản thân báo cáo đó đã là phát hiện có giá trị về chất lượng spec.

### 4.5 Đa ngôn ngữ (L8)

Khi làm trên bản tiếng Nhật: cần tokenizer riêng cho tìm kiếm từ khóa, embedding đa ngôn ngữ, và **ghép bản EN với bản JP theo cấu trúc heading** để xem song ngữ. Việc ghép này còn giúp phát hiện chỗ bản dịch gây hiểu nhầm.

### 4.6 Eval và chatbot (L9)

**Hai tầng đo:**

1. **Retrieval:** tool có tìm đúng section hay quan hệ không (recall@k). Đo sớm, owner xác nhận nhanh.
2. **Answer:** câu trả lời đúng không, có trích dẫn đúng không.

**Khi chuyển sang vòng lặp "sửa → đo → sửa", ba biện pháp chống tối ưu cho điểm số:**

- Giữ một phần golden set **held-out**, không cho agent thấy.
- **Cố định** retriever, model và prompt khi so sánh hai baseline.
- **Owner là cổng cuối.** Điểm số chỉ là đầu vào cho quyết định, không phải quyết định.

Một chỉ số rẻ và có sẵn: **tỷ lệ đề xuất của agent được giữ lại sau review, tính theo từng skill** (lấy từ git log).

### 4.7 Người dùng và UI (L12)

Thứ tự mở rộng: Obsidian (miễn phí, đọc) → Excel cho người ngoài → web UI đọc và duyệt → nhiều người dùng và phân quyền. Web UI gọi cùng CLI hoặc MCP, không viết lại logic.

### 4.8 Vận hành (L13, L14)

Rẻ và nên làm sớm: git hook chạy `specctl validate` và `specctl index` trước commit, và đẩy repo lên một git server nội bộ.

## 5. Kiến trúc đích và đường tiến hóa

```
Bản tạm thời (3 tuần)                    Bản đích (nếu pilot thành công)
─────────────────────                    ────────────────────────────────
vault Markdown + ID          ───giữ──►   vault Markdown + ID  (hoặc JSON canonical nếu L1 đòi hỏi)
meta/ids.json                ───giữ──►   meta/ids.json
index.md, backlinks.md       ──thay──►   SQLite index: FTS5 + vector + edges + context packs
grep                         ──thay──►   search / context / neighbors / impact
specctl CLI                  ───bọc──►   spec-mcp (tool cho mọi harness)
Claude Code + skills         ───giữ──►   Claude Code, Ollama, harness khác (cùng skill)
Obsidian (xem)               ───giữ──►   Obsidian + web UI
Excel export                 ───giữ──►   Excel, Word, ReqIF
golden set thủ công          ──thay──►   eval harness, A/B theo baseline
1 file                       ──mở──►     corpus nhiều file, quan hệ signal, song ngữ
```

**Không có bước nào phải làm lại từ đầu.** Chỉ có một chỗ có thể phải thay dữ liệu: chuyển sang JSON canonical (L1), và ngay cả khi đó ID vẫn được giữ.

## 6. Quyết định để ngỏ và tiêu chí quyết

| # | Quyết định                                                | Quyết khi nào            | Dựa vào                                                                         |
| - | ------------------------------------------------------------ | -------------------------- | --------------------------------------------------------------------------------- |
| 1 | Markdown có đủ làm store không, hay cần JSON canonical | **Tuần 1, ngày 1** | Cổng kiểm tra độ trung thực: bảng ≥ 90%, link ≥ 95%, tỷ lệ text ≥ 0.99 |
| 2 | Có xây index SQLite không                                 | Sau tuần 3                | Tỷ lệ câu hỏi golden set không tìm được bằng từ khóa                  |
| 3 | Có xây spec-mcp không                                     | Sau tuần 3                | Có nhu cầu dùng LLM local hoặc harness khác                                  |
| 4 | Có mở rộng sang nhiều file không                        | Sau pilot                  | Kết quả pilot và nhu cầu thực tế của team                                  |
| 5 | Có làm web UI không                                       | Sau pilot                  | Số người dùng ngoài owner                                                    |
| 6 | Có làm việc trên bản tiếng Nhật không                | Theo khách hàng          | Thỏa thuận với khách hàng                                                    |

## 7. Ưu tiên nếu pilot thành công

| Ưu tiên | Hạng mục                                           | Vì sao                                                         |
| --------- | ---------------------------------------------------- | --------------------------------------------------------------- |
| 1         | L13, L14 (hook và backup)                           | Rẻ, tránh mất dữ liệu và lọt lỗi                        |
| 2         | L3, L4 (index và graph)                             | Nâng chất lượng trả lời và mở ra impact analysis        |
| 3         | L2 (mô tả hình)                                   | Rẻ, bịt một lỗ hổng lớn về nội dung                     |
| 4         | L5 (spec-mcp)                                        | Mở đường cho LLM local và người dùng khác              |
| 5         | L6, L7 (nhiều file, signal)                         | Giá trị lớn nhất về nghiệp vụ, nhưng cần nền ở trên |
| 6         | L9 (eval, chatbot)                                   | Chứng minh giá trị ở quy mô lớn                           |
| 7         | L1 (JSON canonical), L8 (tiếng Nhật), L12 (web UI) | Đắt, chỉ làm khi có yêu cầu rõ                          |

## 8. Điều quan trọng nhất cần nhớ

Giá trị của giải pháp **không nằm ở định dạng lưu trữ, cũng không nằm ở công cụ**. Nó nằm ở hai thứ:

1. **ID bất biến cho từng block** — cho phép định vị, theo dõi thay đổi, truy vết và báo cáo.
2. **Tập quan hệ được trích ra từ tài liệu** — cho phép hiểu ngữ cảnh và đánh giá tác động.

Mọi thứ còn lại (Markdown hay JSON, grep hay SQLite, Claude Code hay harness khác, Obsidian hay web UI) đều là lựa chọn có thể thay đổi mà không phá hỏng hai thứ trên.
