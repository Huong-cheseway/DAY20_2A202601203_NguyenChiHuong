# Exit Ticket - Step 5

Question source: [docs/lab_guide.md#L111](docs/lab_guide.md#L111)

## 1) Khi nao NEN dung multi-agent? Vi sao?

Case cu the:
- Bai toan nghien cuu can tong hop nhieu nguon va phai co citation ro rang (vi du: so sanh kien truc single-agent vs multi-agent voi yeu cau giai thich trade-off, do tin cay nguon, va trich dan).

Ly do dua tren so lieu benchmark cua chinh bai nay:
- Multi-agent dat quality proxy = 10.0, citation coverage = 100%, failure rate = 0%.
- Single-agent dat quality proxy = 3.5, citation coverage = 0%, failure rate = 0%.
- Du lieu tham chieu: [reports/benchmark_report.md#L8](reports/benchmark_report.md#L8), [reports/benchmark_report.md#L9](reports/benchmark_report.md#L9), [reports/benchmark_report.md#L15](reports/benchmark_report.md#L15).

Ket luan:
- Nen dung multi-agent khi muc tieu la chat luong tong hop + kha nang truy vet chung cu, chap nhan them chi phi/latency de doi lay do tin cay va kha nang giai thich.

## 2) Khi nao KHONG nen dung multi-agent? Vi sao?

Case cu the:
- Cac truy van ngan, don buoc, khong can tong hop nhieu nguon (vi du: hoi dinh nghia, tom tat ngan, cau hoi FAQ ky thuat co pham vi hep).

Ly do dua tren so lieu benchmark cua chinh bai nay:
- Single-agent nhanh hon (4.79s vs 25.04s) va re hon (0.0004 USD vs 0.0010 USD).
- Du lieu tham chieu: [reports/benchmark_report.md#L8](reports/benchmark_report.md#L8), [reports/benchmark_report.md#L9](reports/benchmark_report.md#L9), [reports/benchmark_report.md#L13](reports/benchmark_report.md#L13), [reports/benchmark_report.md#L14](reports/benchmark_report.md#L14).

Ket luan:
- Khong nen dung multi-agent cho tac vu don gian vi single-agent da du tot, nhanh hon, re hon, va de van hanh hon.

## Tong ket learning outcome

- Multi-agent khong luon thang baseline; no manh o bai toan can phan vai, handoff, va verification.
- Baseline van la lua chon hop ly cho bai toan nhe, uu tien toc do va chi phi.
