# Case study: AI tạo sinh và mức tiếp xúc nghề nghiệp

## Câu hỏi

Những nghề nào có nhiệm vụ tiếp xúc nhiều hơn với AI tạo sinh, và tỷ lệ việc làm trong các nhóm nghề tiếp xúc khác nhau ra sao theo thu nhập quốc gia, giới? Đây là phân tích **mô tả** từ nghiên cứu ILO năm 2025. Chỉ số tiếp xúc không đo tỷ lệ mất việc hay tác động nhân quả của AI.

## Nguồn và đơn vị quan sát

| Tệp đầu vào | Đơn vị quan sát | Cách lấy | Nguồn |
| --- | --- | --- | --- |
| `data/ilo_occupations.csv` | 427 mã nghề ISCO-08 bốn chữ số | Trích toàn bộ bảng A1, chuẩn hóa nhãn nhóm và điểm số, giữ trang in của từng dòng | [ILO Working Paper 140](https://www.ilo.org/sites/default/files/2025-05/WP140_web.pdf), trang 48–61 |
| `data/ilo_tasks.csv` | 3.265 mục nhiệm vụ gắn với 427 mã nghề | Trải phẳng JSON dạng cây được bài báo liên kết; tách điểm số khỏi chuỗi mô tả nhiệm vụ | [Dữ liệu trực quan của tác giả](https://pgmyrek.github.io/2025_GenAI_scores_ISCO08/output_data.json), được Working Paper nhắc ở trang 37 |
| `data/ilo_indicators.csv` | 10 chỉ số tổng hợp đã xuất bản | Ghi chép thủ công từ văn bản báo cáo, mỗi dòng có tài liệu và trang in | [ILO Research Brief](https://www.ilo.org/sites/default/files/2025-05/Research%20brief_FINAL_15May2025_21.05.25_1.pdf), trang 7; Working Paper, trang 36 và 44 |
| `analysis/selected_occupations.csv` | 6 nghề minh họa | Quyết định biên tập; nối với bảng A1 bằng mã ISCO | Dự án này |

**Hai mẫu số khác nhau:** 427 là số *mã nghề* trong bảng A1; 23,8% và các tỷ lệ theo thu nhập, giới là tỷ lệ *việc làm* do ILO ước tính. Không dùng 112/427 để suy ra tỷ lệ người lao động tiếp xúc. Con số 29.753 trong bài báo là số nhiệm vụ của hệ phân loại Ba Lan được mô hình chấm; JSON công khai dùng ở đây có 3.265 mục nhiệm vụ ở cấu trúc ISCO-08. Hai con số này không phải cùng một tập bản ghi.

## Quy trình tái lập

Chỉ cần Python 3 và `pdfplumber` cho bước trích bảng PDF; phiên bản đã dùng được ghim trong `requirements-analysis.txt`. Phần làm sạch tiếp theo dùng thư viện chuẩn, gồm `csv`, `sqlite3` và `decimal`.

```powershell
python -m pip install -r requirements-analysis.txt
python analysis/extract_table_a1.py --check
python analysis/extract_task_tree.py --check
python analysis/build_data.py --check
```

Hai lệnh trích xuất tải nguồn công khai, kiểm tra SHA-256 đã ghim rồi so sánh với bản CSV lưu trong dự án. Có thể thêm `--pdf <đường-dẫn>` hoặc `--json <đường-dẫn>` để dùng bản nguồn tải sẵn. Bỏ `--check` để tạo lại CSV sau khi đã xem xét thay đổi ở nguồn. `build_data.py` chạy offline từ ba CSV đầu vào, thực thi [`analysis/queries.sql`](analysis/queries.sql) trong SQLite và sinh các tệp `data/occupation_profile.csv`, `data/occupation_reconciliation.csv`, `data/story-data.json`, `data/story-data.js`. Trang web đọc `story-data.js`.

SHA-256 nguồn đang dùng:

| Nguồn | SHA-256 |
| --- | --- |
| Research Brief PDF | `510cbb3722fb0e089cb0e0a587a5a3eeb4bb2efde95ea6f1ef0cd8522e7db31a` |
| Working Paper 140 PDF | `9077761c72aabaa3c7ee70999ec5aa46a6afcf943b5fb01baa971f601d363ee9` |
| JSON nhiệm vụ | `c73052a0fb47d2df5d40c5c886c264cc20984e3fbad0631a0f1f9bde1cd3d98b` |

## Kiểm tra chất lượng

1. Bảng A1 có 427 mã nghề duy nhất, đủ sáu nhãn nhóm; bốn nhóm 1–4 có lần lượt 17, 44, 38, 13 mã, cộng thành **112**, khớp báo cáo ILO.
2. JSON có 3.265 mục nhiệm vụ, phủ đủ 427 mã nghề. Mã, nhóm và điểm nhiệm vụ được kiểm tra trước khi nối. Điểm đều thuộc khoảng 0–1.
3. SQL tính lại điểm trung bình của từng nghề từ các mục nhiệm vụ. **426/427 nghề** có độ lệch không quá 0,01 so với điểm được in trong bảng A1 (bao gồm sai khác do làm tròn).
4. Ngoại lệ là ISCO **7126, Plumbers and Pipe Fitters**: bảng A1 in **0,18**, trung bình từ năm điểm trong JSON là **0,1515**, lệch **0,0285**. Dự án giữ **0,18** khi trình bày dữ liệu phụ lục và lưu cả hai giá trị trong `data/occupation_reconciliation.csv`. Hai nguồn công khai khác nhau ở dòng này; dữ liệu hiện có chưa xác định được nguyên nhân.
5. Sáu mã nghề được chọn phải tồn tại trong bảng A1. Dữ liệu xuất ra được kiểm tra lại bằng `build_data.py --check`; trang được duyệt trên desktop và hai kích thước di động bằng `smoke_test.py`.

## Phép tính và kết quả

| Kết quả | Phép tính | Cách đọc |
| --- | --- | --- |
| 23,8% việc làm toàn cầu thuộc nhóm 1–4 | 20,5% nhóm 1–3 + 3,3% nhóm 4 | Hai thành phần được Research Brief công bố; tổng là giá trị suy ra |
| 76,2% ngoài nhóm 1–4 | 100% − 23,8% | Giá trị suy ra, không phải một dòng gốc |
| Lưới 100 ô | 76 ô ngoài nhóm, 21 ô nhóm 1–3, 3 ô nhóm 4 | Làm tròn để minh họa; các ô không phải mẫu 100 người được khảo sát |
| 23 điểm phần trăm cách biệt theo thu nhập | 34% nước thu nhập cao − 11% nước thu nhập thấp | Hai tỷ lệ gốc đã được báo cáo làm tròn đến số nguyên |
| 112/427 mã nghề thuộc nhóm 1–4 | Đếm mã trong bảng A1 bằng SQL | Tỷ lệ mã nghề, **không phải** tỷ lệ việc làm |

Ở nhóm tiếp xúc 4, tỷ lệ việc làm của nữ và nam lần lượt là 4,7% và 2,4% trên toàn cầu; tại nước thu nhập cao là 9,6% và 3,5%. Đây là các tỷ lệ có mẫu số riêng theo giới, nên không cộng chúng để thành tỷ lệ chung. Bảng A1 cũng cho thấy khoảng điểm trung bình giữa các nhóm có chồng lấn; ILO phân nhóm dựa trên cả điểm trung bình và độ phân tán của nhiệm vụ (Working Paper, trang 37). Không nên tự suy nhóm chỉ từ điểm trung bình.

## Giới hạn

- Bảng A1 và JSON nhiệm vụ không chứa số người làm từng nghề. Phân tích số mã nghề là **không trọng số**.
- Các tỷ lệ việc làm là ước tính tổng hợp của ILO, không được tính lại từ hai tệp cấp nghề và nhiệm vụ trong dự án này.
- Sáu nghề trên trang được chọn để thể hiện phổ điểm, không phải top 6 nghề và không đại diện thống kê cho tất cả nghề.
- Mức tiếp xúc mô tả khả năng AI tác động đến nhiệm vụ ở thời điểm nghiên cứu; không đo mức áp dụng thực tế, số việc làm mất đi, thu nhập hay việc làm mới.
