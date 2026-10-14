# Trạng thái bàn giao — Eviaura · Day 26

Kiệt đã làm phần triển khai chính. Phần bổ sung lần này tập trung vào
kiểm chứng và hồ sơ, không thay mã agent/prosecutor hoặc nội dung deck.

- [x] Ba artifact `agent/`, `deck/`, `eval/` có mặt.
- [x] Thêm 14 ca tích hợp cho 8 cơ chế và replica; lưu trace trong JUnit.
- [x] Chạy đầy đủ trên Ubuntu/Python 3.12: 4.655 pass, 7 skip, 0 lỗi.
- [x] Gate PASS; deck 0 lỗi/1 cảnh báo; prosecutor 34/34 claim đúng.
- [x] Kiểm tra 36 cấu hình spar theo bot, role và seed.
- [x] Workflow Linux qua actionlint; pipeline tương ứng đã chạy cục bộ.
- [x] Đồng bộ tên đội và điền username của cả ba thành viên.
- [x] Tạo bundle, xác minh file/hash và đóng gói hồ sơ.
- [ ] Push workflow để có kết quả GitHub Actions.
- [ ] Nhóm chốt bài và nộp lên hệ thống giảng viên.
- [ ] Kiểm chứng harness thật: hook trước ANSWER, freshness và các lỗi
  đã tái hiện. Chi tiết trong [report](docs/DAY26_REVIEW.md).

Các test skip và kết quả spar không chứng minh cách ly kernel hay chất
lượng tournament. Không sửa kit/bot/fixture để làm xanh kiểm tra.

Bài chính: `submissions/Eviaura.bundle`. Hồ sơ đi kèm:
`submissions/Eviaura-hoso.zip`; xem [SUBMISSION.md](SUBMISSION.md).
