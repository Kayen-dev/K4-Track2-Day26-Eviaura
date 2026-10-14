# Hồ sơ nộp — Eviaura · Day 26

**Nhóm:** Trần Nguyễn Trí Dũng (`bananayass`), Kiệt (`kayendev`), Phong (`phong123-ai`). Phạm vi từng người ở [TEAMMATES.md](TEAMMATES.md).

**Bài nộp chính:** `submissions/Eviaura.bundle`, tạo bằng `make submit TEAM=Eviaura`. Bundle chứa 13 tệp thuộc `agent/`, `deck/`, `eval/`; manifest và 39 hash kit đã được kiểm tra khớp với thư mục hiện tại.

**Hồ sơ đi kèm:** `submissions/Eviaura-hoso.zip`, gồm bundle, tài liệu, test bổ sung và log/trace của audit. ZIP chỉ để bàn giao; định dạng lab nhận là `.bundle`.

Kiểm tra cục bộ trên Linux/Python 3.12: 4.680 test pass, 7 skip; validator deck 0 lỗi, 1 cảnh báo; 34/34 cáo buộc đúng trên 40 fixture; 36 lượt spar. **Dải sát thương chưa được chứng minh:** trong cấu hình `all`, Adversary seed 5 còn 0 HP, nhưng phép thử đối chứng với lineup toàn blank cũng hạ bot ở seed đó. Audit ghi cảnh báo, không dùng HP của spar làm kết luận về riêng deck. Chi tiết ở [report](docs/DAY26_REVIEW.md).

Workflow Linux cần secret `WORLD_RELEASE_TOKEN` có quyền đọc release riêng của giảng viên. Chưa có kết quả GitHub Actions hoặc xác nhận nộp trên hệ thống giảng viên. `TEAM_PLAN.md` được giữ nguyên theo yêu cầu.
