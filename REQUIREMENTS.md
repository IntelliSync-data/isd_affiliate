# isd_affiliate: Yêu cầu chức năng (bản 2, đã cập nhật theo góp ý)

> Trạng thái: **đã làm xong** (xem README.md). Mục 5: hoá đơn tự động, hoa hồng, phạm vi đơn ngoài Profile Management để bản sau; deploy ehub trước; SO tạm dùng tiền tệ công ty.
> Nền tảng: Odoo 18, LGPL-3.

---

## 1. Mục tiêu

Quản lý người tiếp thị liên kết (affiliate):

- Affiliate tự đăng ký tài khoản qua link trên domain Odoo, trở thành user **Portal** và **không vào được backend** `/odoo`.
- Mỗi affiliate có **mã thành viên** `XXXX-XXXX-XXXX` (chỉ chữ số) và **link giới thiệu** theo nguồn mạng xã hội (`?ref=…&ssm=…`).
- Đơn hàng mua từ link giới thiệu được ghi nhận **đúng affiliate**, xem được trên danh sách Sale Order.
- Package của Profile Management gắn được với một **sản phẩm**. Đơn của package đó sinh **Sale Order** đi song song: tạo đơn là "Quotation Sent", trả đủ tiền là "Sales Order".

---

## 2. Một module duy nhất: `isd_affiliate`

**Phụ thuộc:**
- `contacts`, `portal`, `auth_signup`
- `sale`: có sẵn Product và Invoicing, nên form affiliate có nút "Invoiced"
- `isd_profile_management`

Cài `isd_affiliate` là có đủ toàn bộ tính năng bên dưới.

- Nút "Opportunities" trên form Contact chỉ hiện nếu DB có cài CRM. Module **không** bắt buộc CRM.
- Phần chọn sản phẩm cho Package nằm trong `isd_affiliate`, hiện trên form Package của Profile Management. Nhờ vậy `isd_profile_management` không phải phụ thuộc thêm Sales cho những khách không dùng affiliate.

---

## 3. Chức năng chi tiết

### F1. Loại contact "Affiliate" (tiếng Việt: "Tiếp thị liên kết")

- Ô chọn loại trên form Contact hiện có *Individual / Company*. Thêm lựa chọn thứ ba: **Affiliate**.
- Về bản chất, affiliate là **một cá nhân** (`is_company = False`), được đánh dấu thêm `is_affiliate = True`.
  - Bỏ chọn Affiliate thì quay về Individual.
  - Mã thành viên vẫn giữ lại để lịch sử đơn hàng không mất liên kết.
- Chuyển một contact sang Affiliate thì tự sinh mã thành viên (F3) nếu contact đó chưa có mã.

### F2. Menu và danh sách affiliate

```
Affiliate
├── Affiliates       (menu đầu tiên)
├── Sources
└── Configuration
```

- **Affiliates:** dạng thẻ (kanban) giống trang Contacts, có thêm danh sách (list). Chỉ hiện contact là affiliate.
  - Điều kiện lọc affiliate được **gắn cứng vào action**, không phải filter trên thanh tìm kiếm. Bỏ hết filter thì vẫn chỉ thấy affiliate.
  - Tạo mới từ menu này thì contact mặc định là Affiliate.
- **Mở chi tiết:** dùng **form Contact chuẩn** (có ô chọn loại Affiliate). Trên form có thêm:
  - Mã thành viên (F3)
  - Ô chọn nguồn + link giới thiệu (F4)
  - Smart button **Đơn đã giới thiệu** (số đơn và tổng tiền đã thanh toán), bấm vào mở danh sách Sale Order có affiliate này
  - Hai smart button chuẩn **Opportunities** (nếu có CRM) và **Invoiced**, vẫn giữ. Đây là đơn affiliate *tự mua*.
- **Phân quyền:** chỉ nhóm **Affiliate Manager** (và Admin) thấy menu này.
- **Trạng thái duyệt** (khi bật duyệt tay, xem F6): cột/nhãn "Chờ duyệt" / "Đã duyệt" trên thẻ, kèm nút **Duyệt** và **Từ chối** trên form.

### F3. Mã thành viên

- **Định dạng:** `XXXX-XXXX-XXXX`, X là chữ số 0–9. Ví dụ `4821-0937-1564`.
- **Sinh ngẫu nhiên**, **không trùng** trên toàn DB, có ràng buộc ở mức database. Sinh trùng thì sinh lại.
- **Chỉ đọc** trên form. Nhãn: "Affiliate Code" / "Mã thành viên".

### F4. Link giới thiệu (backend)

- **Công thức:** `[Base URL trong Configuration]` + `?ref=<mã thành viên>&ssm=<key của nguồn>`
  - Ví dụ: `https://bloompod.vn/?ref=4821-0937-1564&ssm=tiktok`
  - Nếu Base URL đã có sẵn `?` thì nối bằng `&` để link vẫn đúng.
- Trên form affiliate: ô **Nguồn** (chỉ nguồn đang Active), bên cạnh là ô **Link** chỉ đọc, có nút copy. Đổi nguồn thì link đổi theo.
- Link được **tính ra** chứ không lưu cứng. Đổi Base URL thì link của mọi affiliate đổi theo.

### F5. Nguồn mạng xã hội (menu Sources)

| Trường | Bắt buộc | Ghi chú |
|---|---|---|
| Tên | ✔ | Hiện trong ô chọn nguồn |
| Mô tả | | |
| Key | ✔ | Tự điền khi gõ tên: "TikTok" → `tiktok`, "Facebook Ads" → `facebook-ads`, bỏ dấu tiếng Việt. Vẫn sửa tay được. Chỉ cho chữ thường, số, `-`, `_`. Không trùng. |
| Icon | | Upload ảnh (png, jpg, ico, svg, webp) |
| Trạng thái | ✔ | Active / Inactive. Chỉ nguồn Active mới hiện trong ô chọn. |

- **Dữ liệu mẫu sẵn khi cài:** Facebook, TikTok, Instagram, YouTube, Zalo, Website. Xoá hoặc tắt được.
- **Nguồn đã dùng trong đơn hàng thì không xoá được, chỉ tắt (Inactive)**, để thống kê cũ vẫn đúng.

### F6. Configuration

| Cấu hình | Mặc định | Ý nghĩa |
|---|---|---|
| **Base URL** cho link giới thiệu | trống | Cấu hình riêng của module, **không** đổi `web.base.url` của Odoo. Trống thì chưa có link. |
| **Cho phép tự đăng ký** | Bật | Tắt thì trang đăng ký báo "đang đóng". |
| **Duyệt tay trước khi hoạt động** | Tắt | Bật thì affiliate mới đăng ký ở trạng thái **Chờ duyệt**: vẫn đăng nhập xem được trang của mình, nhưng **chưa có link** và `ref` của họ **chưa được ghi nhận** vào đơn cho tới khi quản lý bấm Duyệt. |

**Không có cấu hình "user mặc định".** Affiliate luôn là user Portal:
- tạo từ mẫu Portal sẵn có của Odoo
- tự gắn thêm nhóm "Affiliate"
- không đụng tới user mặc định dùng cho đăng ký thường

### F7. Trang tự đăng ký (trên domain Odoo)

- Trang công khai `/affiliate/register`, gồm form: họ tên, email, điện thoại, mật khẩu, nhập lại mật khẩu, đồng ý điều khoản.
- Khi gửi form:
  1. Tạo user **Portal**, gắn nhóm Affiliate.
  2. Contact đi kèm được đặt loại **Affiliate**, tự sinh mã thành viên. Nếu bật duyệt tay thì ở trạng thái Chờ duyệt.
  3. Tự đăng nhập, rồi chuyển tới trang affiliate (F8).
- **Chống lạm dụng:**
  - Email trùng user khác thì báo lỗi.
  - Giới hạn số lần đăng ký theo IP.
  - Mật khẩu tối thiểu 8 ký tự.
- **Email đã có contact** (ví dụ khách hàng cũ, chưa có user) thì gắn vào đúng contact đó, không tạo contact trùng.
- Trang đăng nhập Odoo (`/web/login`) có thêm link "Đăng ký làm affiliate" khi đang bật tự đăng ký.

### F8. Trang thông tin riêng cho affiliate (trên domain Odoo)

User Portal **không vào được** `/odoo`. Sau khi đăng nhập, họ được đưa tới `/my/affiliate`:

- Họ tên, mã thành viên, trạng thái (Chờ duyệt / Đã duyệt).
- **Ô chọn nguồn**: chọn nguồn nào thì hiện link của nguồn đó (có icon), kèm nút **Copy**.
- Thống kê đơn đã giới thiệu:
  - số đơn, tổng tiền đã thanh toán
  - danh sách đơn gồm ngày, gói/sản phẩm, số tiền, trạng thái
  - **Không** hiện tên, email hay số điện thoại người mua.
- Sửa thông tin cá nhân và đổi mật khẩu: dùng trang "My Account" có sẵn của Odoo.

### F9. Package → sản phẩm

- Trên form tạo/sửa **Package** của Profile Management có thêm ô **Sản phẩm**, không bắt buộc. Chọn được sản phẩm có sẵn, hoặc tạo nhanh ngay trong ô đó.
- Nút **"Tạo sản phẩm từ package"**: tạo sản phẩm dạng dịch vụ cùng tên và giá với package, rồi gắn vào luôn.
- Phải hiện đúng trên cả bản thường lẫn bản override `.bloompod` / `.vfo` của Profile Management. Khi làm sẽ kiểm tra từng bản.

### F10. Đơn Profile Management → Sale Order

Chỉ áp dụng cho package **đã gắn sản phẩm**. Package không gắn sản phẩm thì chạy như hiện tại, không sinh Sale Order.

| Sự kiện trên đơn Profile Management | Sale Order |
|---|---|
| Tạo đơn (qua API hoặc tay) | Tạo SO: khách hàng = contact của đơn; 1 dòng sản phẩm của package với giá = **giá thực của đơn**; điền Affiliate và Nguồn; trạng thái **Quotation Sent** (không tự gửi email cho khách) |
| Sửa giá đơn khi chưa thanh toán | Cập nhật giá dòng SO |
| Thanh toán một nửa (`half_paid`) | **Không đổi**: vẫn Quotation Sent |
| **Thanh toán đủ** (`paid`): đây là "thanh toán thành công" | **Xác nhận SO** → **Sales Order** |
| Huỷ đơn | Huỷ SO |
| Hoàn tiền (`returned`) | **Không tự động làm gì**: bàn sau |

- **Thời điểm đồng bộ:** gắn vào lúc đơn đổi `payment_status`. Mọi đường thanh toán hiện có (webhook, xác nhận chuyển khoản tay, nút "Mark Paid") đều đi qua đó.
- **Liên kết hai chiều:** đơn Profile Management có ô "Sale Order", SO có ô "Profile Order".
- **Lỗi khi tạo SO không được làm hỏng việc tạo đơn của khách.** Đơn vẫn được tạo, lỗi ghi vào log, và có nút "Tạo lại Sale Order" trên đơn.

### F11. Cột Affiliate trên Sale Order

- Thêm trường **Affiliate** (chỉ chọn được contact là affiliate) và **Nguồn** trên SO. Đây là trường liên kết thật. **Không** dùng lại "Customer Reference".
- Trên danh sách SO:
  - có cột **Affiliate** (ẩn/hiện được)
  - có filter "Từ affiliate"
  - gom nhóm được theo Affiliate và theo Nguồn
- SO tạo tay vẫn chọn được affiliate.

### F12. API: frontend gửi `ref` lên

- Frontend đọc `ref` và `ssm` trên URL, lưu lại (cookie/localStorage, khuyến nghị 30 ngày), rồi gửi kèm khi tạo đơn.
- Thêm vào payload của `POST /api/profile/create` (không bắt buộc, các trường hiện có giữ nguyên):

```json
{
  "package_id": 123,
  "email": "user@example.com",
  "...": "các trường hiện có giữ nguyên",
  "affiliate_ref": "4821-0937-1564",
  "affiliate_source": "tiktok"
}
```

- **Backend xử lý:**
  - Tìm affiliate **đã duyệt** theo mã, và nguồn theo key. Ghi vào đơn, rồi vào SO.
  - **Mã sai, chưa duyệt hoặc thiếu thì bỏ qua và vẫn tạo đơn bình thường.**
  - **Tự giới thiệu chính mình** (email người mua trùng email affiliate) thì không ghi nhận affiliate.
- `POST /api/profile/order-info` trả thêm mã và tên hiển thị của affiliate, không có email/số điện thoại.

---

## 4. Dữ liệu (tóm tắt kỹ thuật)

**`res.partner`**
- `is_affiliate`
- `company_type` thêm lựa chọn `affiliate`
- `affiliate_code` (duy nhất, chỉ đọc)
- `affiliate_state` (`pending` / `approved` / `rejected`)
- `affiliate_source_id` (dùng để dựng link trên form)
- `affiliate_link` (tính toán)

**`isd.affiliate.source`**
- `name`, `description`, `key` (duy nhất), `icon`, `active`

**Cấu hình**
- `isd_affiliate.base_url`
- `isd_affiliate.signup_enabled`
- `isd_affiliate.require_approval`

**`sale.order`**
- `affiliate_id`, `affiliate_source_id`, `profile_order_id`

**`profile.management`**
- `product_id`

**`user.profile`**
- `affiliate_id`, `affiliate_source_id`, `sale_order_id`

**Nhóm quyền**
- **Affiliate Manager** (backend): quản lý affiliate, nguồn, cấu hình, duyệt.
- **Affiliate** (portal): chỉ xem dữ liệu của chính mình (record rule).

---

## 5. ❓ Còn cần chốt

1. **Hoá đơn:** khi SO thành "Sales Order" (thanh toán đủ), có cần **tự tạo hoá đơn** không? Đề xuất: chưa, dừng ở Sales Order.
2. **Hoa hồng** để bản sau? Bản này đã ghi đủ affiliate và nguồn trên từng đơn, sau này tính hoa hồng chỉ là thêm phần mới.
3. **Phạm vi đơn:** bản này chỉ gắn affiliate cho đơn Profile Management và SO tạo tay. Sau này có cần cho website shop hay POS không?
4. **Deploy:** repo GitHub riêng `isd_affiliate`? Lên những server nào (bloompod, vfo, ehub, kclickphoto)?
5. **Tiền tệ:** giá trong Profile Management chưa gắn tiền tệ (việc `pm_currency` còn treo). SO tạm dùng tiền tệ của công ty. Có khách nào bán bằng nhiều loại tiền không?

---

## 6. Ngoài phạm vi bản này

- Xử lý hoàn tiền (`returned`) trên SO: bàn sau.
- Tính và chi trả hoa hồng.
- Affiliate nhiều cấp.
- Đăng nhập bằng Google/Facebook cho affiliate.

---

## 7. Kiểm thử và bàn giao

- **Test tự động:**
  - mã không trùng, đúng định dạng
  - link đúng khi Base URL có hoặc không có `?`
  - key nguồn tự sinh
  - đăng ký tạo user Portal đúng nhóm, user mặc định của Odoo không đổi
  - affiliate không vào được `/odoo` và không xem được dữ liệu người khác
  - danh sách affiliate không lộ contact thường kể cả khi bỏ hết filter
  - duyệt tay: chưa duyệt thì `ref` không được ghi nhận
  - `ref` sai và tự giới thiệu
  - SO đồng bộ theo từng trạng thái thanh toán
  - lỗi tạo SO không làm hỏng đơn
- **Tour UI trên Chrome:** đăng ký → trang affiliate → chọn nguồn → copy link.
- **Thử upgrade trên DB có sẵn Profile Management**, gồm cả bản `.bloompod` / `.vfo`.
- **Bản dịch tiếng Việt.** README gồm cấu hình và định dạng API cho frontend.
