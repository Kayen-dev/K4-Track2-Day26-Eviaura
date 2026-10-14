# Kế hoạch nhóm — Day 26 Colosseum

**Thành viên:** Dũng, Kiệt, Phong  
**Tên đội/bundle:** `kayendev-lutech`  
**Nguyên tắc:** Kiệt nhận phần kiểm tra nhẹ vì đã làm trước đó; Dũng và Phong xử lý phần cải thiện còn lại. Phân công này có thể đổi sau khi cả nhóm xác nhận.

## Điểm xuất phát

- Đã có mã cho `agent/`, `deck/`, `eval/` và bundle cục bộ.
- Bộ test công khai: 4.633 pass, 5 skip; 3 test gốc không chạy được trên môi trường Windows/path hiện tại nên được loại khỏi lượt kiểm tra.
- Deck: 0 lỗi validator trên world thật, còn 1 cảnh báo về *lethality band* vì kết quả đấu thật không thể chứng minh hoàn toàn bằng validator.
- Prosecutor: 34/34 cáo buộc đúng trên 40 fixture công khai. Đây là kết quả fixture, chưa bảo đảm hiệu quả với trace mới.
- Spar seed 3, vai trò `all`: thắng rookie 100–0, operator 100–0, adversary 72–13. Spar dùng `MockBroker`, nên cần đọc trace và thử nhiều seed trước khi kết luận.

## Phân công

| Người | Mức việc | Đầu việc | Kết quả cần bàn giao |
| --- | --- | --- | --- |
| **Dũng** | Chính | Hoàn thiện phòng thủ trong `agent/` | Mã, test tình huống, ghi chú giới hạn của luồng `ANSWER` |
| **Phong** | Chính | Kiểm tra prosecutor trên trace mới và giảm cáo buộc thiếu/sai | Danh sách ca bỏ lỡ có nguyên nhân, thay đổi detector nếu cần, test hồi quy |
| **Kiệt** | Nhẹ | Rà deck và kiểm chứng kết quả đấu | Bảng ngắn kết quả validator/spar, đề xuất tối đa 1–2 sửa đổi có bằng chứng |

### Dũng — agent

- [ ] Xác định chỗ nào trong luồng được phép kiểm tra `ANSWER` trước khi gửi. Các hàm ở `agent/guardrails.py` hiện chưa được gọi tự động; **không sửa `kit/`** để ép tích hợp. Nếu kit không có hook, ghi rõ giới hạn và tăng hướng dẫn trong `agent/prompt.md`.
- [ ] Rà `Gateway.decide` về route/replica và ngân sách xuyên 10 vòng. Chỉ nối `agent/strategy.py` khi có dữ liệu đầu vào đáng tin và có thể kiểm tra bằng test; tránh đoán replica hoặc từ chối mọi lệnh.
- [ ] Viết test cho các trường hợp thực sự rủi ro: lease hết hạn, sai learner/audience, write thiếu precondition, mặt nạ field tốn credit và tình huống replica lệch.
- [ ] Bàn giao: mô tả thay đổi, test đã chạy và giới hạn còn lại của agent.

### Phong — prosecutor

- [ ] Xem các mục `MISSED` trong spar. Kiểm tra xem `protocol_misuse` bị bỏ qua vì giới hạn **một claim mỗi family** hay do detector không tìm được bằng chứng; không thêm claim chỉ để hết dòng `MISSED`.
- [ ] Thử trace/seed ngoài 40 fixture hiện có và rà nguy cơ false claim, nhất là các detector ngữ nghĩa và bằng chứng `answer.span`.
- [ ] Nếu sửa `eval/prosecute.py`, giữ ≤4 claims, ≤1 claim/family, mỗi claim có bằng chứng hợp lệ và argument ≤400 ký tự.
- [ ] Bàn giao: 2–3 ca đại diện (trace, nhận định, kết quả), test hồi quy cho lỗi được sửa.

### Kiệt — deck

- [ ] Xác nhận 14 thẻ, lineup 10 thẻ và `validate_deck.py` trên world thật vẫn hợp lệ.
- [ ] Chạy spar với rookie và adversary ở vài seed khác seed 3; ghi thẻ nào kích hoạt, thẻ nào không, và phân biệt điểm từ **deck** với điểm từ **prosecutor**.
- [ ] Chỉ đề xuất sửa `deck/` nếu tìm được thẻ không chạm mục tiêu hoặc thứ tự lineup có bằng chứng là kém. Nếu ổn, ghi “giữ nguyên” và kết thúc phần việc.
- [ ] Bàn giao: một bảng kết quả ngắn và kết luận giữ/sửa deck.

## Ghép bài và kiểm tra cuối — Dũng + Phong

- [ ] Rà thay đổi để bảo đảm không sửa `kit/`, `bots/`, `fixtures/`; mã trong `agent/`, `deck/`, `eval/` chỉ dùng standard library.
- [ ] Chạy `python -m kit.gate_no_key`, bộ test, `validate_deck.py` với `kit/world/df8c55dabb35`, và spar với ít nhất rookie + adversary.
- [ ] Tạo lại bundle sau **mọi** thay đổi trong `agent/`, `deck/`, `eval/`: `python -m kit.submit --team kayendev-lutech`.
- [ ] Kiểm tra manifest/hash trong bundle, rồi mới coi bản nộp là bản cuối.

Lệnh kiểm tra trên PowerShell (3 test được loại trừ là các ca gốc không tương
thích Windows/path hiện tại; ghi rõ chúng trong báo cáo kiểm tra):

```powershell
.\.venv\Scripts\python.exe -m kit.gate_no_key
.\.venv\Scripts\python.exe -m pytest tests/ -q -k "not test_path_id_over_the_real_corpus_has_no_collisions and not test_compute_etag_over_real_corpus_bodies_reproduces and not test_run_probe_vectors_unsandboxed_baseline"
.\.venv\Scripts\python.exe validate_deck.py deck/deck.json deck/lineup.json --world kit/world/df8c55dabb35
.\.venv\Scripts\python.exe -m kit.submit --team kayendev-lutech
```

`TEAMMATES.md` và file kế hoạch này để nhóm phối hợp trong repo; công cụ nộp chỉ đóng gói `agent/`, `deck/`, `eval/`.
