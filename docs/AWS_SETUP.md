# AWS S3 Kurulum Kılavuzu (PROMPT 4)

## 1. Terraform ile Bucket Oluşturma

`infra/s3.tf` (yeni bir `infra/` dizini açıp bu içerikle oluşturabilirsiniz):

```hcl
resource "aws_s3_bucket" "lumiere_uploads" {
  bucket = "lumiere-user-uploads-prod"
}

resource "aws_s3_bucket_versioning" "lumiere_uploads" {
  bucket = aws_s3_bucket.lumiere_uploads.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lumiere_uploads" {
  bucket = aws_s3_bucket.lumiere_uploads.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" }
  }
}

resource "aws_s3_bucket_public_access_block" "lumiere_uploads" {
  bucket                  = aws_s3_bucket.lumiere_uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "lumiere_uploads" {
  bucket = aws_s3_bucket.lumiere_uploads.id
  rule {
    id     = "archive-old-uploads"
    status = "Enabled"
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "lumiere_uploads" {
  bucket = aws_s3_bucket.lumiere_uploads.id
  cors_rule {
    allowed_methods = ["PUT", "GET"]
    allowed_origins = ["https://app.lumiere-coaching.com"]
    allowed_headers = ["*"]
    max_age_seconds = 3000
  }
}

resource "aws_iam_user" "lumiere_backend" {
  name = "lumiere-backend-s3"
}

resource "aws_iam_user_policy" "lumiere_backend_s3" {
  user = aws_iam_user.lumiere_backend.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
      Resource = "${aws_s3_bucket.lumiere_uploads.arn}/*"
    }]
  })
}
```

Uygulama:
```bash
cd infra && terraform init && terraform apply
```

## 2. Backend Ortam Değişkenleri

Terraform çıktısındaki erişim anahtarlarını `backend/.env`'e ekleyin:
```bash
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=eu-central-1
S3_BUCKET_NAME=lumiere-user-uploads-prod
S3_KMS_KEY_ID=alias/aws/s3   # veya özel KMS anahtarınız
CLOUDFRONT_DOMAIN=cdn.lumiere-coaching.com   # opsiyonel CDN
```

## 3. Maliyet Tahmini (kabaca)

| Kalem | Tahmini Aylık Maliyet (1000 aktif kullanıcı) |
|---|---|
| S3 depolama (video/ses, ~50MB/kullanıcı) | ~$1.15 (Standard) |
| S3 PUT/GET istekleri | ~$2-5 |
| CloudFront çıkış trafiği | Kullanıma bağlı, ~$5-20 |
| Glacier arşiv (90 gün sonrası) | ~$0.004/GB/ay |

Gerçek maliyet kullanım desenine göre değişir; AWS Cost Explorer + bütçe
alarmı (`aws budgets create-budget`) kurulması önerilir.

## 4. Yapılandırılmadığında Davranış

`AWS_ACCESS_KEY_ID`/`S3_BUCKET_NAME` tanımlı değilse `backend/storage.py`
tüm S3 fonksiyonlarında `None` döner; `/api/v1/files/presigned-url` endpoint'i
HTTP 501 ile "S3 yapılandırılmadı" mesajı döner. Mevcut onboarding video/ses
akışı (`/api/onboarding/video`, `/api/onboarding/voice`) bundan etkilenmez,
yerel diske yazmaya devam eder.
