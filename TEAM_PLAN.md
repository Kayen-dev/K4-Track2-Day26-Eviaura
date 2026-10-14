# Kế hoạch nhóm — Day 26 Colosseum

**Thành viên:** Dũng, Kiệt, Phong

**Tên đội dự kiến:** `Eviaura`

**Phân công:** Dũng và Phong xử lý phần kỹ thuật còn mở. Kiệt chỉ rà và xác nhận deck vì đã làm trước đó; không giao lại việc đã xong.

## 1. Kết luận rà soát và điểm xuất phát

**Chưa thể đánh dấu lab hoàn tất.** Ba artifact đã có mã và đã tạo bundle theo tên cũ, nhưng chưa chứng minh đầy đủ hiệu quả trong đấu thật, chưa giải quyết khoảng trống kiểm tra `ANSWER`, và tên đội đang không đồng nhất.

- Đã có mã cho `agent/`, `deck/`, `eval/` và bundle cục bộ theo tên cũ.
- Bộ test công khai: 4.633 pass, 5 skip; 3 test gốc không chạy được trên môi trường Windows/path hiện tại nên được loại khỏi lượt kiểm tra.
- Deck: 0 lỗi validator trên world thật, còn 1 cảnh báo về *lethality band* vì kết quả đấu thật không thể chứng minh hoàn toàn bằng validator.
- Prosecutor: 34/34 cáo buộc đúng trên 40 fixture công khai. Đây là kết quả fixture, chưa bảo đảm hiệu quả với trace mới.
- Spar seed 3, vai trò `all`: thắng rookie 100–0, operator 100–0, adversary 72–13. Spar dùng `MockBroker`, nên cần đọc trace và thử nhiều seed trước khi kết luận. Các số trên là baseline, chưa phải bằng chứng lab đã xong.

## 2. Việc chung trước khi sửa mã

- [ ] Thống nhất tên đội `Eviaura`. Hiện plan dùng `Eviaura`, còn `TEAMMATES.md`, `deck/deck.json` và bundle hiện có dùng `kayendev-lutech`. Đồng bộ các tên này trước khi nộp; bundle cũ không phải bản cuối.
- [ ] Điền GitHub username của Dũng, Kiệt, Phong trong `TEAMMATES.md` và xác nhận phân công thực tế.
- [ ] Xác nhận `kit/world/df8c55dabb35/manifest.json` có mặt, world đúng 12.375 trang và **không** có `truth.json`. Không commit world hoặc bundle vào Git.
- [ ] Mỗi thay đổi có người phụ trách và ghi ngắn: lỗi quan sát được, cách sửa, test chứng minh. Không sửa `kit/`, `bots/`, `fixtures/`.

## 3. Phân công còn lại

| Người | Mức việc | Đầu việc | Kết quả cần bàn giao |
| --- | --- | --- | --- |
| **Dũng** | Chính | Hoàn thiện phòng thủ trong `agent/` | Mã, test tình huống, ghi chú giới hạn của luồng `ANSWER` |
| **Phong** | Chính | Kiểm tra prosecutor trên trace mới và giảm cáo buộc thiếu/sai | Danh sách ca bỏ lỡ có nguyên nhân, thay đổi detector nếu cần, test hồi quy |
| **Kiệt** | Nhẹ | Rà deck và kiểm chứng kết quả đấu | Bảng ngắn kết quả validator/spar, đề xuất tối đa 1–2 sửa đổi có bằng chứng |

### Dũng — agent

- [ ] Rà luồng thật của `Gateway.decide`: route theo header/replica, lease còn hiệu lực, scope/learner/audience, write có `If-Match` và `Idempotency-Key`, field mask và ngân sách dùng chung 10 vòng. Chỉ nối `agent/strategy.py` khi có dữ liệu đầu vào đáng tin và test tái hiện được; tránh deny toàn bộ hoặc chọn replica theo hằng số.
- [ ] Rà các cơ chế README §6: kết quả partial/continuation, rate limit, lỗi `unavailable`, `lang`, tool deprecated. Xác định cơ chế nào gateway kiểm tra được và cơ chế nào chỉ agent/prompt xử lý được; thêm test cho khoảng trống quan trọng.
- [ ] Xác định có hook hợp lệ để gọi `check_grounding`, scanner, redaction, kiểm tra số **trước `ANSWER`** hay không. `Gateway.decide` không nhận `ANSWER`; **không sửa `kit/`** để ép tích hợp. Nếu không có hook, ghi rõ giới hạn và làm chặt `agent/prompt.md` với kiểm tra anchor đã truy xuất, trường `require`, xung đột nguồn và thông tin riêng tư.
- [ ] Chạy spar vai trò `defender` với rookie, operator, adversary ở nhiều seed; ghi lỗi phòng thủ còn lặp lại. Test thêm ít nhất lease, write, audience, credit và replica khi thay đổi mã.
- [ ] Bàn giao: mô tả thay đổi, test đã chạy, ca tái hiện và giới hạn còn lại của agent.

### Phong — prosecutor

- [ ] Chạy `eval.prosecute` trên 40 fixture và kiểm tra đủ 17 lớp lỗi; sau đó thử trace spar/seed mới. Với từng `MISSED`, phân biệt **family cap** (đã chọn lỗi nặng hơn cùng family) với detector thiếu bằng chứng; không thêm claim chỉ để hết dòng `MISSED`.
- [ ] Rà claim ngữ nghĩa dễ false positive: `hallucination`, `ungrounded`, `guardrail_breach`, `unflagged_conflict`, `overreach`, `incoherent`, `non_responsive`, `unsupported_precision`. Chỉ nộp khi evidence trong L1 đủ để chứng minh; không suy diễn từ telemetry riêng hoặc đáp án thật không có trong trace.
- [ ] Giữ hợp đồng: đồng bộ, không I/O, dưới 5 giây; ≤4 claims, ≤1/family; mỗi claim có `cls`, 1–4 evidence refs, `expected`, `observed`, `argument` ≤400 ký tự. Ưu tiên precision vì claim sai bị trừ `0.8 × weight`.
- [ ] Chạy spar vai trò `prosecutor` với cả ba bot và đọc claim bị `FALSE`, `UNPROVEN`, `MISSED`. Nếu sửa detector, thêm test hồi quy từ ca thực tế.
- [ ] Bàn giao: 2–3 trace đại diện, lý do chọn/bỏ claim, kết quả trước/sau và test hồi quy cho lỗi được sửa.

### Kiệt — deck

- [ ] Xác nhận 10 attack + 4 blank, lineup 10 ID không lặp; ≥3 MCP, ≥3 A2A, ≥2 gateway, ≥6 class; `replica_flip` trỏ path trong drift set; ask/anchor và target tồn tại trong world thật.
- [ ] Chạy `validate_deck.py`, rồi spar vai trò **`attacker`** với rookie và adversary ở vài seed khác seed 3. Ghi thẻ nào kích hoạt, thẻ nào không, và phân biệt sát thương do **deck** với điểm từ **prosecutor** ở vai trò `all`.
- [ ] Chỉ đề xuất sửa `deck/` nếu tìm được thẻ không chạm mục tiêu hoặc thứ tự lineup có bằng chứng là kém. Nếu ổn, ghi “giữ nguyên” và kết thúc phần việc.
- [ ] Bàn giao: một bảng kết quả ngắn và kết luận giữ/sửa deck.

## 4. Ghép bài và tiêu chí hoàn thành — Dũng + Phong

- [ ] Đọc `RULES.md` lần cuối; rà `git diff` để không đưa thay đổi ở `kit/`, `bots/`, `fixtures/`; `agent/`, `deck/`, `eval/` chỉ dùng standard library và không dùng network/I/O trong hai hàm bị giới hạn.
- [ ] Chạy gate cấm API key, test, deck validator trên world thật và spar riêng `defender`, `attacker`, `prosecutor`, sau đó `all`. Ghi bot, seed, role, HP, claim sai/bỏ lỡ và credit; không chỉ ghi “thắng”.
- [ ] Kiểm tra các giới hạn runtime: `Gateway.decide` trả `Decision` hợp lệ dưới 250 ms; `prosecute` dưới 5 giây và đúng quota claim. Chạy test liên quan sau mọi sửa mã.
- [ ] Xác nhận tên đội thống nhất trong `TEAM_PLAN.md`, `TEAMMATES.md`, `deck/deck.json` và lệnh nộp. Tạo lại `submissions/Eviaura.bundle` **sau thay đổi cuối** trong `agent/`, `deck/`, `eval/`.
- [ ] Mở bundle, kiểm tra `MANIFEST.json` có team `Eviaura`, đủ file thuộc ba thư mục và hash nội dung khớp. Không dùng bundle `kayendev-lutech.bundle` làm bản nộp cuối.
- [ ] Trước session start, chốt `agent/` và `deck/` vì hai phần này khóa khi phiên bắt đầu; `eval/` có thể tiếp tục cải thiện theo luật. Ghi rõ giới hạn còn lại nếu chưa có bằng chứng để đóng một mục.

Lệnh kiểm tra trên PowerShell (3 test được loại trừ là các ca gốc không tương
thích Windows/path hiện tại; ghi rõ chúng trong báo cáo kiểm tra):

```powershell
.\.venv\Scripts\python.exe -m kit.gate_no_key
.\.venv\Scripts\python.exe -m pytest tests/ -q -k "not test_path_id_over_the_real_corpus_has_no_collisions and not test_compute_etag_over_real_corpus_bodies_reproduces and not test_run_probe_vectors_unsandboxed_baseline"
.\.venv\Scripts\python.exe -m eval.prosecute
.\.venv\Scripts\python.exe validate_deck.py deck/deck.json deck/lineup.json --world kit/world/df8c55dabb35
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe spar.py --bot rookie --as attacker --rounds 10 --seed 4
.\.venv\Scripts\python.exe spar.py --bot adversary --as all --rounds 10 --seed 4
.\.venv\Scripts\python.exe -m kit.submit --team Eviaura
```

Các lệnh spar ở trên chỉ là ví dụ; bảng kết quả cuối phải có nhiều seed và các role cần thiết. Trên Linux/CI, chạy `python -m pytest tests/` đầy đủ để kiểm tra lại 3 ca đang bị loại trên Windows.

`TEAMMATES.md` và file kế hoạch này để nhóm phối hợp trong repo; công cụ nộp chỉ đóng gói `agent/`, `deck/`, `eval/`.
