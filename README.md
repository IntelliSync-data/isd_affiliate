# Affiliate (isd_affiliate)

Tiếp thị liên kết cho Odoo 18. Người tiếp thị tự đăng ký, có mã thành viên và link giới thiệu theo từng mạng xã hội. Đơn hàng mua qua link được ghi nhận đúng người tiếp thị, và đơn của Profile Management sinh Sale Order tương ứng.

Phụ thuộc: `contacts`, `portal`, `auth_signup`, `sale`, `isd_profile_management`.

## Cài đặt và cấu hình

1. Cài module **Affiliate (by ISD)** trong Apps.
2. Vào **Affiliate → Configuration** (chỉ admin hệ thống):
   - **Base URL**: nơi link giới thiệu trỏ tới, ví dụ `https://bloompod.vn`. Đây là cấu hình riêng, không đổi `web.base.url` của Odoo.
   - **Open Sign-up**: mở trang đăng ký `/register-affiliate`. Mặc định là bật.
   - **Approve New Affiliates**: người mới đăng ký phải chờ duyệt. Khi bật, họ chưa có link và `ref` của họ chưa được ghi nhận cho tới khi quản lý bấm **Approve** trên form của họ.
3. **Affiliate → Sources**: các mạng xã hội (Facebook, TikTok, Instagram, YouTube, Zalo, Website có sẵn).
   - Key tự điền từ tên và sửa được.
   - Chỉ nguồn **Active** mới hiện trong ô chọn.
   - Nguồn đã dùng trong đơn thì không xoá được, chỉ chuyển sang Inactive.
4. Trên **Package** của Profile Management, chọn **Product**, hoặc bấm **Create from package** để tạo sản phẩm dịch vụ cùng tên và giá. Chỉ package có sản phẩm mới sinh Sale Order.
5. Gán nhóm **Affiliate Manager** (Thiết lập → Người dùng) cho người quản lý tiếp thị. Admin có sẵn nhóm này.

## Người tiếp thị

- **Loại liên hệ:** liên hệ có thêm loại thứ ba **Affiliate / Tiếp thị liên kết**, bên cạnh Individual và Company.
- **Mã thành viên:** `XXXX-XXXX-XXXX` (chỉ chữ số), sinh ngẫu nhiên, không trùng.
- **Link giới thiệu:** `<Base URL>?ref=<mã>&ssm=<key nguồn>`. Nếu Base URL đã có `?` thì nối bằng `&`.
- **Menu Affiliate → Affiliates:** chỉ hiện người tiếp thị. Điều kiện lọc gắn cứng vào menu, bỏ hết filter cũng không lộ liên hệ khác.
- **Các trang dành cho người tiếp thị** (không có header/footer của website):

  | Trang | Dùng để |
  |---|---|
  | `/register-affiliate` | tự đăng ký |
  | `/login-affiliate` | đăng nhập; tài khoản không phải người tiếp thị bị từ chối |
  | `/my-affiliate` | trang riêng, có nút Log out |

  - Đăng nhập xong, kể cả qua `/web/login`, người tiếp thị được đưa thẳng tới `/my-affiliate`.
  - Địa chỉ cũ `/affiliate/register` và `/my/affiliate` tự chuyển sang địa chỉ mới.
- **Tự đăng ký:**
  - Tạo user **Portal** từ mẫu Portal sẵn có của Odoo, gắn thêm nhóm "Affiliate (portal)".
  - Người tiếp thị **không vào được** `/odoo`; mở `/odoo` sẽ bị đưa về `/my`.
  - Email đã có liên hệ (khách cũ) thì dùng lại liên hệ đó.
- **Trang riêng `/my-affiliate`:**
  - mã thành viên
  - chọn nguồn để hiện link, có nút Copy
  - số đơn đã giới thiệu, tổng tiền đơn đã thanh toán
  - danh sách đơn, **không** hiện thông tin người mua

## Đơn hàng

Đơn Profile Management của package có sản phẩm sinh Sale Order đi kèm:

| Đơn Profile Management | Sale Order |
|---|---|
| Tạo đơn | Tạo SO ở trạng thái **Quotation Sent** (không gửi email), điền Affiliate và Nguồn |
| Sửa giá khi chưa thanh toán | Cập nhật giá trên SO |
| Trả một nửa | Không đổi, vẫn Quotation Sent |
| **Trả đủ** | Xác nhận SO → **Sales Order** |
| Huỷ | Huỷ SO |
| Hoàn tiền | Chưa tự động: xử lý tay |

**Lưu ý:**
- Giá trên SO là đúng số khách trả, **không cộng thuế**.
- Lỗi khi tạo SO không làm hỏng đơn của khách: đơn vẫn được tạo, lỗi ghi vào log, và form đơn có nút **Create Sale Order** để tạo lại.

Trên danh sách Sale Order có cột **Affiliate**, filter "From an Affiliate", và gom nhóm được theo Affiliate và theo Nguồn.

## API cho frontend

### 1. Lưu `ref` khi khách vào trang

Khi URL có `?ref=...&ssm=...`, frontend lưu hai giá trị này lại (khuyến nghị 30 ngày, cookie hoặc localStorage) để dùng khi khách đặt hàng.

### 2. Gửi kèm khi tạo đơn: `POST /api/profile/create`

Thêm hai trường, đều không bắt buộc. Các trường hiện có giữ nguyên:

```json
{
  "jsonrpc": "2.0",
  "params": {
    "package_id": 123,
    "email": "khach@example.com",
    "name": "Nguyen Van A",
    "affiliate_ref": "4821-0937-1564",
    "affiliate_source": "tiktok"
  }
}
```

| Trường | Ý nghĩa |
|---|---|
| `affiliate_ref` | giá trị `ref` trên URL (mã thành viên) |
| `affiliate_source` | giá trị `ssm` trên URL (key của nguồn) |

Backend **không bao giờ từ chối đơn** vì `ref`. Mã sai, người tiếp thị chưa được duyệt, hoặc khách tự giới thiệu chính mình (cùng liên hệ hoặc cùng email) thì đơn vẫn tạo bình thường, chỉ là không ghi nhận người tiếp thị. Key nguồn sai hoặc không có (link chung, không kèm `ssm=`) thì vẫn ghi nhận người tiếp thị, nguồn mặc định là **Website**.

### 3. Xem lại: `POST /api/profile/order-info`

Trong `result.order` có thêm khoá `affiliate`. Khoá này là `null` nếu đơn không có người tiếp thị:

```json
"affiliate": {"code": "4821-0937-1564", "name": "Tran Thu Ha", "source": "tiktok"}
```

Khoá này chỉ có mã, tên hiển thị và key nguồn, không có email hay số điện thoại của người tiếp thị.
