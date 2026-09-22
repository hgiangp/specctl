# specctl

Biến một bản đặc tả yêu cầu hệ thống dạng Word thành một tập file Markdown có mã ID bất biến,
để AI agent đọc hiểu và cải thiện được nó — với bằng chứng đo được rằng không có nội dung nào
bị mất và không có con số nào bị đổi âm thầm.

**Bắt đầu từ [`docs/F-features.md`](docs/F-features.md)** — vấn đề, phương pháp, và thứ tự tính năng.

| Tài liệu | Dùng để |
|---|---|
| [`docs/F-features.md`](docs/F-features.md) | Đọc trước. Đang giải bài gì, giải bằng cách nào, làm gì trước |
| [`docs/D-implementation-spec.md`](docs/D-implementation-spec.md) | Đặc tả kỹ thuật chi tiết từng quy tắc (v2.1) |
| [`docs/G-data-contract.md`](docs/G-data-contract.md) | Tám quyết định về hợp đồng dữ liệu, và lý do từng cái |
| [`docs/B-limitations-roadmap.md`](docs/B-limitations-roadmap.md) | Cái gì cố tình bỏ, khi nào nên đầu tư thêm |
| [`docs/H-testing.md`](docs/H-testing.md) | Cách chạy test, thêm fixture, và so sánh với pandoc |
| [`docs/archive/`](docs/archive/) | Lịch sử. Không implement từ đây |

## Chạy thử

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                                              # 296 passed, 8 skipped
python scripts/spike_coverage.py source/SYS.docx    # tài liệu thật chứa gì
```

Chi tiết, kể cả cách so sánh với pandoc: [`docs/H-testing.md`](docs/H-testing.md).
