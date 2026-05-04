# Hướng dẫn Deploy & CI/CD cho RAG QABot

Tài liệu này ghi lại cách triển khai production cho project theo hướng **deploy CPU tiết kiệm chi phí**, đồng thời giải thích vai trò của **GitHub Actions (CI/CD)**.

---

## 1. GitHub Actions là gì?

GitHub Actions là hệ thống automation của GitHub, dùng để chạy các quy trình tự động khi có sự kiện như `push`, `pull_request`, `release`.

- **CI (Continuous Integration)**: tự chạy lint/test/build khi push code.
- **CD (Continuous Delivery/Deployment)**: tự động đưa bản build lên môi trường chạy (registry/VPS).

> Kết luận: GitHub Actions có thể dùng cho cả CI và CD.

---

## 2. Có cần GitHub để deploy không?

Không bắt buộc 100%, nhưng rất nên dùng.

### Không dùng GitHub

Vẫn deploy được theo kiểu thủ công:
1. Build image ở local.
2. Push image lên registry.
3. SSH vào VPS, pull image và restart container.

Phù hợp demo nhanh, nhưng khó kiểm soát version và rollback.

### Dùng GitHub + Actions (khuyến nghị)

Flow chuẩn:
1. Push code lên repo.
2. Actions chạy check/test/build.
3. Push image lên GHCR/Docker Hub.
4. VPS pull image mới và restart.

Ưu điểm:
- Rõ commit nào đang chạy.
- Dễ rollback theo tag image.
- Chuẩn CI/CD production.

---

## 3. GitHub Actions có tự chạy ngay không?

Không. Cần setup ban đầu một lần.

## 4. Checklist setup GitHub Actions (1 lần)

- [ ] Tạo workflow file trong repo: `.github/workflows/ci.yml` (và/hoặc `deploy.yml`).
- [ ] Đảm bảo GitHub Actions được bật trong repository settings.
- [ ] Thiết lập trigger:
  - [ ] `on: push` cho branch `main`.
  - [ ] `on: pull_request` cho kiểm tra trước merge.
- [ ] Cấu hình workflow permissions nếu push container image:
  - [ ] `packages: write`
  - [ ] `contents: read`
- [ ] Thêm repository secrets cần thiết:
  - [ ] `OPENAI_API_KEY` (nếu test cần gọi dịch vụ).
  - [ ] `GHCR_PAT` (nếu không dùng `GITHUB_TOKEN` mặc định).
  - [ ] `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` (nếu deploy qua SSH).
- [ ] Kiểm tra workflow chạy thành công ở tab Actions.

> Sau khi setup xong, mỗi lần push thì pipeline sẽ tự chạy theo định nghĩa trong workflow.

---

## 5. Production deploy cho project này: cần gì trên VPS?

VPS mới tinh cần đủ 4 phần:

1. Docker + Docker Compose.
2. Image chứa code app (pull từ registry).
3. File `.env` production (secrets/config).
4. Dữ liệu RAG `artifacts/` (đặc biệt `database_semantic`) được mount vào container.

> [!IMPORTANT]
> Kéo mỗi image mà không có `artifacts/database_semantic` thì RAG không có knowledge base để retrieve.

---

## 6. Phân tách đúng giữa code và data

- **Code**: nằm trong image (qua `COPY . /app` khi build production).
- **Data runtime**: nằm ngoài image, mount bằng volume (`/app/artifacts`).
- **Model cache**: mount volume riêng (`/app/.cache/huggingface`) để tránh tải lại model mỗi lần recreate container.

Công thức vận hành:

```txt
App chạy được = image(code) + env(secrets) + artifacts(data)
```

---

## 7. Luồng CI/CD khuyến nghị (CPU production)

1. Developer push code lên `main`.
2. GitHub Actions chạy CI:
   - kiểm tra backend/frontend,
   - build Docker target `prod-cpu`.
3. Push image lên GHCR với tag theo commit SHA.
4. CD step (hoặc thao tác tay qua SSH):
   - VPS pull image mới,
   - restart service bằng docker compose.
5. Verify endpoint và log.

---

## 8. Khi nào cần build lại image?

Cần build image mới khi:
- sửa code backend/frontend,
- đổi dependencies,
- đổi Dockerfile.

Không bắt buộc build lại image khi:
- chỉ đổi `.env` trên VPS,
- chỉ update dữ liệu `artifacts` (nếu mount volume ngoài).

---

## 9. Checklist triển khai thực tế

- [ ] Chuẩn hóa Dockerfile production (`prod-cpu`) và compose production.
- [ ] Tạo workflow CI build/push image.
- [ ] Chuẩn bị VPS: Docker, thư mục `/opt/rag-qabot`, `.env`, artifacts.
- [ ] Mount `artifacts` + `hf cache` vào container.
- [ ] Deploy bản đầu tiên và kiểm tra chat endpoint.
- [ ] Ghi lại quy trình rollback theo tag image.
- [ ] Cập nhật checklist này sau mỗi bước hoàn thành.
