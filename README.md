# Flobstar News Intelligence Backend

Python/FastAPI backend for the Flobstar News Intelligence & Automated Newsroom System.

## Features

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: Async ORM for database operations
- **RSS Feed Parser**: Automated news source polling
- **Web Scraper**: Extract content from news articles
- **Background Task Scheduler**: Periodic source polling
- **Authentication**: JWT-based authentication with Supabase
- **Structured Logging**: Comprehensive logging with structlog

## Project Structure

```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   ├── sources.py    # News sources CRUD
│   │   ├── stories.py    # News stories CRUD
│   │   ├── assignments.py # Story assignments CRUD
│   │   └── notifications.py # Notifications CRUD
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration settings
│   │   ├── database.py   # Database session management
│   │   ├── logging.py    # Logging configuration
│   │   └── auth.py       # Authentication middleware
│   ├── models/           # SQLAlchemy models
│   │   ├── news_source.py
│   │   ├── source_health_history.py
│   │   ├── news_story.py
│   │   ├── story_assignment.py
│   │   ├── story_status_history.py
│   │   ├── ai_generation.py
│   │   ├── news_notification.py
│   │   └── audit_log.py
│   ├── services/         # Business logic services
│   │   ├── rss_parser.py
│   │   └── web_scraper.py
│   ├── tasks/            # Background tasks
│   │   └── source_poller.py
│   ├── scheduler.py      # Task scheduler
│   └── main.py           # Application entry point
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
└── README.md           # This file
```

## Installation

1. **Create a virtual environment:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

## Configuration

Required environment variables:

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role key
- `SUPABASE_DB_HOST`: Database host (from Supabase connection string)
- `SUPABASE_DB_PORT`: Database port (default: 5432)
- `SUPABASE_DB_NAME`: Database name (default: postgres)
- `SUPABASE_DB_USER`: Database user (default: postgres)
- `SUPABASE_DB_PASSWORD`: Database password

Optional variables:
- `OPENAI_API_KEY`: For AI content generation (OpenAI GPT-4)
- `ANTHROPIC_API_KEY`: Alternative AI provider (Anthropic Claude)
- `MISTRAL_API_KEY`: Cost-effective AI provider (Mistral AI)
- `REDIS_URL`: For Celery background tasks

## Running the Backend

### Development Mode

```bash
python -m app.main
```

This will start the server on `http://localhost:8000` with auto-reload enabled.

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Health Check
- `GET /health` - Health check endpoint

### News Sources
- `GET /api/v1/sources` - List all sources
- `GET /api/v1/sources/{source_id}` - Get specific source
- `GET /api/v1/sources/{source_id}/health` - Get source health history
- `POST /api/v1/sources` - Create new source (service role)
- `PUT /api/v1/sources/{source_id}` - Update source (service role)
- `DELETE /api/v1/sources/{source_id}` - Archive source (service role)

### News Stories
- `GET /api/v1/stories` - List all stories
- `GET /api/v1/stories/{story_id}` - Get specific story
- `POST /api/v1/stories` - Create new story
- `PUT /api/v1/stories/{story_id}` - Update story
- `PATCH /api/v1/stories/{story_id}/status` - Update story status
- `DELETE /api/v1/stories/{story_id}` - Archive story
- `GET /api/v1/stories/stats/dashboard` - Get dashboard statistics

### Story Assignments
- `GET /api/v1/assignments` - List all assignments
- `GET /api/v1/assignments/{assignment_id}` - Get specific assignment
- `POST /api/v1/assignments` - Create new assignment
- `PUT /api/v1/assignments/{assignment_id}` - Update assignment
- `PATCH /api/v1/assignments/{assignment_id}/accept` - Accept assignment
- `PATCH /api/v1/assignments/{assignment_id}/complete` - Complete assignment
- `PATCH /api/v1/assignments/{assignment_id}/reject` - Reject assignment
- `DELETE /api/v1/assignments/{assignment_id}` - Cancel assignment

### Notifications
- `GET /api/v1/notifications` - List notifications for user
- `GET /api/v1/notifications/{notification_id}` - Get specific notification
- `POST /api/v1/notifications` - Create new notification
- `PATCH /api/v1/notifications/{notification_id}/read` - Mark as read
- `PATCH /api/v1/notifications/recipient/{recipient_id}/read-all` - Mark all as read
- `DELETE /api/v1/notifications/{notification_id}` - Delete notification
- `GET /api/v1/notifications/recipient/{recipient_id}/unread-count` - Get unread count

## Background Tasks

The backend includes a background task scheduler that:

1. **Polls RSS feeds** every 15 minutes (configurable)
2. **Extracts new stories** from feeds
3. **Deduplicates** stories by URL
4. **Tracks source health** (response time, error rate)
5. **Logs health history** for monitoring

The scheduler starts automatically when the application starts and stops gracefully on shutdown.

## Authentication

API endpoints use JWT-based authentication with Supabase:

- **Regular endpoints**: Require authenticated user
- **Sensitive operations** (create/update/delete sources): Require service role

Include the JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Database Models

The backend uses SQLAlchemy async models that mirror the Supabase database schema:

- `NewsSource`: RSS/API/web scraper configurations
- `SourceHealthHistory`: Historical health data
- `NewsStory`: Detected news stories
- `StoryAssignment`: User assignments
- `StoryStatusHistory`: Status change history
- `AIGeneration`: AI-generated content
- `NewsNotification`: User notifications
- `AuditLog`: Activity tracking

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development Notes

- The backend uses async/await throughout for performance
- Database sessions are managed via dependency injection
- All endpoints return JSON responses
- Error handling includes proper HTTP status codes
- Structured logging for debugging and monitoring

## Testing

To test the backend:

```bash
# Run tests (when implemented)
pytest

# Run with coverage
pytest --cov=app
```

## Future Enhancements

- [ ] Add AI content generation endpoints
- [ ] Implement Celery for distributed task processing
- [ ] Add rate limiting
- [ ] Implement caching with Redis
- [ ] Add API versioning
- [ ] Create webhook integrations
- [ ] Add comprehensive test suite
