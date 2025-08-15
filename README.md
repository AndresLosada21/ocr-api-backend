# OCR API Backend

A simple yet powerful backend API for Optical Character Recognition (OCR), barcode scanning, and QR code reading. Built with FastAPI, PaddleOCR, and PostgreSQL. Perfect for integrating text extraction and code scanning into your applications.

This is a personal project I built to experiment with image processing and API development. It supports processing images for text extraction, detecting various barcode types, and reading/generating QR codes. Everything is containerized with Docker for easy setup.

## Features

- **OCR Processing**: Extract text from images using PaddleOCR with support for multiple languages (e.g., Portuguese, English).
- **Barcode Scanning**: Detect and read barcodes like EAN13, CODE128, QR_CODE, etc., using Pyzbar.
- **QR Code Handling**: Read QR codes from images and generate new ones.
- **Batch Processing**: Handle multiple images in one go.
- **Job Management**: Asynchronous job queue with status tracking, results retrieval, and cancellation.
- **Analytics**: Usage statistics, error reports, and performance metrics.
- **Health Checks**: Endpoints to monitor API and service health.
- **Database Integration**: PostgreSQL for storing job history and results, with Alembic migrations.
- **Rate Limiting & Security**: Basic rate limiting and API key validation.
- **Docker Support**: Easy deployment with Docker Compose, including PgAdmin for DB management.

## Tech Stack

- **Framework**: FastAPI
- **OCR Engine**: PaddleOCR
- **Barcode/QR**: Pyzbar & qrcode
- **Database**: PostgreSQL + SQLAlchemy + Alembic
- **Image Processing**: OpenCV & Pillow
- **Containerization**: Docker & Docker Compose
- **Others**: Uvicorn (server), Psutil (monitoring), Pytest (testing)

## Installation

### Prerequisites

- Python 3.10+
- Docker (if using containerized setup)
- PostgreSQL (if running locally without Docker)

### Local Setup (Without Docker)

1. Clone the repo:
   ```
   git clone https://github.com/yourusername/ocr-api-backend.git
   cd ocr-api-backend
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Copy `.env.example` to `.env` and fill in your values (e.g., `DATABASE_URL=postgresql://user:pass@localhost/ocr_api`).

5. Set up the database:
   - Create the database: `createdb ocr_api` (or use your DB tool).
   - Run migrations: `alembic upgrade head`.

6. Run the server:
   ```
   uvicorn app.main:app --reload
   ```
   The API will be available at `http://localhost:8000`.

### Docker Setup (Recommended)

1. Clone the repo (as above).

2. Build and start containers:
   ```
   docker-compose up -d --build
   ```

3. Run migrations inside the container:
   ```
   docker exec -it ocr-api alembic upgrade head
   ```

4. Access the API at `http://localhost:8000`.
   - PgAdmin (optional): `http://localhost:5050` (email: admin@ocrapi.local, pass: admin123).

To stop: `docker-compose down`.

## Configuration

Key settings in `.env` or Docker environment:

- `DATABASE_URL`: PostgreSQL connection string.
- `ENABLE_OCR=true`: Toggle features like OCR, barcode, etc.
- `MAX_IMAGE_SIZE_MB=10`: Limit upload size.
- `PADDLE_OCR_LANG=pt`: Default OCR language.
- `RATE_LIMIT_REQUESTS_PER_MINUTE=60`: Rate limiting.

Full list in `app/config/settings.py`.

## Usage

### API Endpoints

The API is documented via Swagger at `http://localhost:8000/docs`.

Key endpoints:

- **Health**: `GET /health` - Check API status.
- **OCR**: `POST /api/v1/ocr/process` - Upload image for text extraction (multipart/form-data).
- **Barcode**: `POST /api/v1/barcode/read` - Scan barcodes from image.
- **QR Code**: `POST /api/v1/qrcode/read` - Read QR codes.
- **Jobs**: `GET /api/v1/jobs/{job_id}` - Get job details.
- **Analytics**: `GET /api/v1/analytics/stats` - Usage summary.

Example with curl (OCR):
```
curl -X POST "http://localhost:8000/api/v1/ocr/process" \
     -F "file=@/path/to/image.jpg" \
     -F "language=pt" \
     -F "enhance_image=true"
```

### Postman Collection

Import `OCR_API_Postman_Collection.json` from the repo into Postman for ready-to-use requests. It covers all endpoints with tests.

### Testing

Run tests:
```
pytest
```

Fixtures and sample images are in `tests/fixtures`.

## Contributing

This is a personal project, but feel free to fork and PR! Issues welcome.

1. Fork the repo.
2. Create a branch: `git checkout -b feature/xyz`.
3. Commit changes.
4. Push and open a PR.

## License

MIT License. See [LICENSE](LICENSE) for details.

## TODOs / Known Issues

- Add authentication (JWT).
- Implement Redis for caching/rate limiting.
- More language support for OCR.
- GPU acceleration for PaddleOCR.
- Webhook support for job completion.

If you find this useful, star the repo! 🚀 Questions? Open an issue.