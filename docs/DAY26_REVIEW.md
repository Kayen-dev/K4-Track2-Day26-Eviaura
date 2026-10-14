# Day 26 — Eviaura · kiểm tra 14/10/2026

Đã dùng world release `df8c55dabb35` của giảng viên: ZIP có SHA-256 `e05327c0bd88b2b1ee9c9194a4bee5535964360d97d462144773d02686705810`, manifest ghi 12.375 trang và không có `truth.json`. Audit tại [results.json](../runs/day26-audit/results.json) dùng Python 3.12, không thay đổi tệp đã theo dõi.

| Kiểm tra | Kết quả |
| --- | --- |
| Full suite | 4.680 pass, 7 skip, 0 lỗi |
| Gate cấm API key/model client | PASS, 109 tệp, 0 vi phạm |
| Deck trên world release | 0 lỗi, 1 cảnh báo R8: validator chỉ dùng proxy, không chứng minh dải sát thương |
| Prosecutor trên fixture | 34/34 claim được xác minh, 0 claim sai, trên 40 fixture và 17 lớp |
| Spar | 36 lượt: 3 bot × 4 role × seed 4, 5, 6; mọi tiến trình thoát mã 0 |
| Bundle chính thức | 13 tệp bài nộp, 39 hash kit khớp, SHA-256 `27581b6c309dd3a08e882dc02e4c2630bd89a68d477bdfe08820181bc3c8df3b` |
| Quan sát HP | Rookie còn 0 HP ở cả ba seed trong role `all`; Adversary còn 13/0/23 HP ở seed 4/5/6. Seed 5 nằm ngoài dải kỳ vọng; chưa thể quy riêng cho deck. |

`spar.py --as attacker` dùng công tố viên của bot làm đường cơ sở; vì vậy các trận hòa 100–100 ở role này không đo được sức tấn công của bộ deck + prosecutor. Role `all` dùng cả ba phần của nhóm. Để kiểm tra tín hiệu HP, tôi thử lineup giả định lặp một lá blank ở cả 10 lượt: Adversary vẫn ngã ở seed 4 và 5 do các lỗi chung của bot bị prosecutor bắt. Lineup giả định này không phải bài nộp. Vì vậy HP của spar cục bộ không chứng minh điều kiện Adversary trụ; audit ghi cảnh báo nhưng không đánh rớt bundle. Validator cũng cảnh báo mutation engine chấm chính thức nằm ở Arena của giảng viên, nên dải sát thương tournament còn cần xác nhận.

Test tích hợp dùng gateway và MCP handler thật trên fixture không có truth; JUnit lưu lệnh, quyết định, kết quả và credit. Query hai hàng khi còn hai credit bị gateway từ chối trước khi trừ phí. Search phiên bản cũ được gateway viết lại thành query. Test khác bao phủ lease, write etag/idempotency, partial/continuation, rate limit, unavailable, lang và replica flip. Chúng kiểm tra các cơ chế cục bộ, không chứng minh chất lượng câu trả lời trong tournament.

Bảy skip gồm kiểm tra corpus riêng của Arena và kiểm tra Seatbelt chỉ chạy trên macOS; không xem đây là bằng chứng cách ly kernel trên Linux. `make doctor` hiển thị 24.750 do cộng cả `__total__` và từng loại trong manifest; số trang chuẩn là 12.375.

[Workflow Linux](../.github/workflows/day26-linux.yml) đã qua actionlint v1.7.12 ở máy cục bộ ([log](../runs/day26-audit/actionlint.log)). Nó tải world từ release riêng bằng `WORLD_RELEASE_TOKEN`, xác minh checksum, chạy audit và lưu log/trace kể cả khi check thất bại. Secret phải có quyền đọc repo `VinUni-AI20k/Day26-Colosseum-Agent-Arena-Kit`; chưa chạy GitHub Actions hoặc nộp lên hệ thống giảng viên.

Chạy lại và đóng gói:

```bash
.venv/bin/python tools/audit_day26.py --team Eviaura
.venv/bin/python tools/package_submission.py
```

Audit ghi log, trace, summary và JUnit trong `runs/day26-audit/`. ZIP hồ sơ chứa các tệp này và ghi `lethality_warnings` trong `DOSSIER_MANIFEST.json`, để người nhận thấy rõ điểm chưa được chứng minh.
