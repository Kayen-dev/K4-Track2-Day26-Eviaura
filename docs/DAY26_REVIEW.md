# Day 26 — Eviaura

Kiệt đã có agent, deck và prosecutor. Theo yêu cầu của Phong, tôi bổ
sung kiểm thử tích hợp, Linux CI và hồ sơ. Giữ nguyên mã xử lý và lá
bài; chỉ đổi nhãn đội thành `Eviaura`. Kiểm tra ngày 14/10/2026.

## Kết quả

| Kiểm tra | Kết quả |
| --- | --- |
| Ubuntu WSL, Python 3.12.15, pytest 8.3.4 | **4.655 pass, 7 skip, 0 lỗi**, không loại test POSIX |
| Tích hợp mới | **14 pass**, bao phủ 8 cơ chế và đổi replica |
| Gate cấm API key/model client | PASS |
| Deck trên world release | 0 lỗi, 1 cảnh báo lethality band |
| Prosecutor | 34/34 claim đúng trên 40 fixture, đủ 17 lớp |
| Spar cục bộ | 36 cấu hình: 3 bot × 4 role × seed 4, 5, 6 |

World `df8c55dabb35` có 12.375 trang, khớp checksum, không có
`truth.json`. Bảy skip do thiếu nguồn gốc/corpus riêng của Arena và
Seatbelt chỉ có trên macOS; không coi đây là bằng chứng cách ly kernel.

## Các tình huống đã thử

Test dùng gateway và MCP handler thật trên **fixture không có truth**.
JUnit lưu lệnh, quyết định, kết quả và credit. Test tái hiện lỗi pass
chỉ xác nhận lỗi tồn tại, không chứng minh agent chặn được lỗi.

| Cơ chế | Quan sát |
| --- | --- |
| Giá động/mask | Catalog được thu hẹp; query 2 hàng khi còn 2 credit vẫn có thể làm credit xuống −1. |
| Lease | Chặn quá 3 lệnh/sang vòng mới khi context cập nhật; server cũng từ chối lease cũ. |
| Write | Server chặn etag cũ; gateway chặn retry cùng key; đọc provenance và đổi etag/key thì ghi thành công. |
| Partial | Cursor gốc phân trang đủ. Token `cont_…` của HardMode gây `bad_request` khi dùng làm cursor query. |
| Rate limit | Server chặn lần thứ ba trong 3 vòng, vẫn tính phí; mở lại vòng 4. |
| Unavailable | Lỗi chỉ có `code`, tái lập theo seed, vẫn tính phí. |
| Lang | Gateway cho qua lang sai; server âm thầm chọn sense khác. |
| Deprecated | Search vẫn được cho qua; server chỉ ra query là successor. Title/1 hàng có cùng giá. |
| Replica | Mutation sau quyết định forward đổi nội dung/envelope; gateway chưa xác minh kết quả. |

Các khoảng trống được ghi lại, không sửa triển khai của Kiệt hoặc kit.
`ANSWER` vẫn cần hook kiểm tra hợp lệ từ harness. Spar dựng sẵn không
chứng minh grounding, ngân sách chung hoặc chất lượng tournament.

## Bàn giao

[Workflow Linux](../.github/workflows/day26-linux.yml) đã qua actionlint,
chạy pipeline test/validator/spar/kiểm tra bundle và lưu bằng chứng.
Đã chạy pipeline cục bộ trên WSL; **chưa chạy GitHub Actions hoặc nộp
bài lên hệ thống giảng viên**. Cấu hình tham khảo
[tài liệu GitHub](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).

Bài chính: `submissions/Eviaura.bundle`. Hồ sơ:
`submissions/Eviaura-hoso.zip`, kèm report, thông tin nhóm và bằng chứng
Linux. Tên đội thống nhất; file/hash bundle đã kiểm tra.

Chạy lại bằng Python 3.12:

```bash
python tools/audit_day26.py --team Eviaura
python tools/package_submission.py
```

Log/trace: `runs/day26-audit/`. Trên Windows, công cụ ghi riêng lỗi
POSIX và lượt tương thích; không đổi lỗi đó thành PASS.
