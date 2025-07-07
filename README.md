# Citis - Permanent Web Archiving SaaS

Citis is a Django-based SaaS application for permanent web archiving and citation. It provides reliable, long-term preservation of web content with permanent shortcodes for academic and professional citation purposes.

## What It Does

Citis competes with services like Perma.cc by offering:

- **Permanent Web Archiving**: Creates immutable snapshots of web pages using SingleFile technology
- **Permanent Citations**: Generates short, permanent URLs for reliable referencing
- **Text Fragment Highlighting**: Allows precise citation of specific text passages within archived content
- **Visit Analytics**: Tracks access patterns, geographic distribution, and usage statistics
- **API-First Design**: Comprehensive REST API for integration with external tools
- **SaaS Features**: User accounts, subscription management, and team collaboration

## Project Structure

The project is organized into modular Django apps:

```
citis/
├── citis/                  # Main Django project settings
├── accounts/               # User authentication and account management
├── archive/                # Web archiving functionality and SingleFile integration
├── analytics/              # Visit tracking and analytics
├── core/                   # Shared utilities and base functionality
├── web/                    # Web UI and dashboard templates
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### Django Apps Overview

- **`accounts/`**: Handles user registration, authentication, subscription management, and team features using django-allauth
- **`archive/`**: Core archiving functionality, integrates with SingleFile, manages shortcodes and archive storage
- **`analytics/`**: Visit tracking, geographic analysis, and usage statistics
- **`core/`**: Shared models, utilities, and base classes used across other apps
- **`web/`**: Django templates and views for the web dashboard and user interface

## Technology Stack

- **Backend**: Django 5.2+ with Django REST Framework
- **Database**: PostgreSQL (with SQLite for development)
- **Authentication**: django-allauth with JWT support
- **Billing**: Stripe integration via dj-stripe
- **Frontend**: Django templates with HTMX for dynamic interactions
- **Archiving**: SingleFile CLI for web content preservation
- **Task Queue**: Celery with Redis for background processing
- **Analytics**: Custom analytics with GeoIP support

## Configuration

The application uses environment-based configuration for maximum flexibility and security. All settings are centralized in `citis/settings.py` and can be customized via environment variables.

### Environment Setup

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Configure your environment variables:**
   - **Required settings**: `SECRET_KEY`, `DATABASE_URL`
   - **Archive settings**: `SINGLEFILE_EXECUTABLE_PATH`, `ARCHIVE_MODE`
   - **Optional services**: `STRIPE_SECRET_KEY`, `REDIS_URL`, `SENTRY_DSN`

3. **Key configuration categories:**

#### Core Django Settings
- `SECRET_KEY`: Django secret key (generate a secure one for production)
- `DEBUG`: Enable/disable debug mode (`True` for development, `False` for production)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hostnames
- `DATABASE_URL`: Database connection string (SQLite for dev, PostgreSQL for production)

#### Archive Configuration
- `ARCHIVE_MODE`: Archive engine (`singlefile`, `archivebox`, or `both`)
- `SINGLEFILE_EXECUTABLE_PATH`: Path to SingleFile CLI binary
- `SINGLEFILE_DATA_PATH`: Directory for storing archives
- `SHORTCODE_LENGTH`: Length of generated shortcodes (default: 5)

#### External Services
- `STRIPE_SECRET_KEY`: Stripe API key for billing (optional)
- `REDIS_URL`: Redis connection for caching and Celery (optional)
- `GEOLITE_DB_PATH`: Path to GeoLite2 database for geographic analytics

#### UI Customization
- `BANNER_BACKGROUND_COLOR`: Overlay banner background color
- `BANNER_LINK_COLOR`: Overlay banner link color
- `BANNER_ACCENT_COLOR`: Overlay banner accent color

### Installation Dependencies

The application includes all necessary dependencies in `requirements.txt`:

- **Core**: Django 5.2+, DRF, django-allauth
- **Database**: PostgreSQL support, database URL parsing
- **Frontend**: Bootstrap 5, HTMX, crispy forms
- **Services**: Stripe billing, Redis caching, Celery tasks
- **Content**: BeautifulSoup, SingleFile integration, GeoIP

### Production Considerations

For production deployment:

1. **Security**: Set `DEBUG=False`, configure `SECURE_*` settings
2. **Database**: Use PostgreSQL via `DATABASE_URL`
3. **Static Files**: Configure `STATIC_ROOT` and use WhiteNoise
4. **Caching**: Set up Redis for caching and Celery
5. **Monitoring**: Configure Sentry for error tracking
6. **Email**: Set up SMTP for account verification

## Data Models

The application's data is organized into several Django models across different apps:

### User Management (accounts app)
- **`CustomUser`** (`accounts/models.py`): Extended Django user model with citis-specific fields
  - Standard Django auth fields (username, email, password)
  - Additional fields: display_name, default_archive_method, is_premium
  - Subscription and usage tracking: monthly_shortcode_limit
  - Helper methods for permission checking and display

### Archive Management (archive app)
- **`Shortcode`** (`archive/models.py`): Core model representing a shortened URL with archiving
  - Primary key: shortcode (unique identifier)
  - Target URL and creation metadata
  - Creator tracking (user, API key, IP address)
  - Text fragment for highlighting specific passages
  - Archive method and status tracking
  - Helper methods for URL generation and analytics

- **`Visit`** (`archive/models.py`): Analytics model tracking each access to a shortcode
  - Timestamp and client information (IP, user agent, referer)
  - Geographic data (country, city) derived from IP
  - Browser and platform detection methods
  - Relationship to shortcode for aggregated analytics

- **`ApiKey`** (`archive/models.py`): API access keys for programmatic usage
  - Primary key: key (generated API key string)
  - Owner user and metadata (name, description)
  - Usage limits (total and daily)
  - Status tracking and usage analytics

### Model Relationships
- **User to API Keys**: One-to-many (users can have multiple API keys)
- **User to Shortcodes**: One-to-many (users can create multiple shortcodes)
- **API Key to Shortcodes**: One-to-many (API keys can create multiple shortcodes)
- **Shortcode to Visits**: One-to-many (shortcodes can have multiple visits)

### Database Indexes
The models include strategic indexes for performance:
- Shortcode creation date, creator user, and creator API key
- Visit timestamp and IP address for analytics queries
- Compound indexes for frequently joined queries

### Legacy Data Migration
The project includes a comprehensive data migration from the original FastAPI implementation:

- **Migration Source**: `fastapi_based/deepcite.db` (SQLite database)
- **Migration Target**: Django ORM models with proper relationships
- **Migrated Data**:
  - 63 shortcodes with full metadata (URLs, timestamps, text fragments)
  - 596 visit records with analytics data
  - 0 API keys (none existed in legacy system)
  - 1 default user created for legacy shortcodes

The migration handles proper foreign key relationships, timestamp conversion, and data integrity verification. All legacy shortcodes are attributed to a default `anonymous_legacy` user to maintain referential integrity.

## Core Services

The application's core business logic is organized into reusable service classes located in the `core/` app. These services handle the primary web archiving functionality and are designed to be framework-agnostic business logic that can be easily tested and reused.

### Service Classes

#### AssetExtractor (`core/services.py`)
Handles extraction of supplementary content from archived pages:
- **Favicon extraction**: Attempts multiple strategies to find and download favicons
- **Screenshot generation**: Creates full-page screenshots using Playwright
- **PDF generation**: Converts web pages to PDF format for offline access
- **Intelligent fallbacks**: Multiple extraction methods with graceful degradation

#### SingleFileManager (`core/services.py`)
Manages SingleFile-based web archiving:
- **Archive creation**: Executes SingleFile CLI tool with proper configuration
- **Duplicate detection**: Identifies and removes identical archives to save storage
- **Asset integration**: Automatically extracts favicons, screenshots, and PDFs
- **File organization**: Structures archives by domain, URL hash, and timestamp
- **Deduplication**: Prevents storing identical content multiple times

#### ArchiveBoxManager (`core/services.py`)
Manages ArchiveBox-based web archiving:
- **API integration**: Communicates with ArchiveBox via REST API
- **Archive retrieval**: Fetches archived content from ArchiveBox storage
- **PDF serving**: Streams PDF downloads with proper headers
- **Multi-extractor support**: Configurable extraction methods (SingleFile, PDF, etc.)
- **Proxy mode**: Supports both direct file access and HTTP proxy modes

### Utility Functions (`core/utils.py`)
Shared utility functions for common operations:
- **Text processing**: `clean_text_fragment()` for display preparation and validation
- **Caching**: `TTLCache` class for time-based cache management with size limits
- **Code generation**: `generate_shortcode()` and `generate_api_key()` for unique identifiers
- **Date parsing**: `parse_ts_str()` for timestamp conversion and validation
- **IP extraction**: `get_client_ip()` for Django request IP detection with Cloudflare support

### Configuration Integration
All services are configured via Django settings variables (loaded from environment):

#### Archive Configuration
- `ARCHIVE_MODE`: Controls which archive engines are active ('singlefile', 'archivebox', or 'both')
- `SHORTCODE_LENGTH`: Length of generated shortcodes (default: 5)
- `TIMEDIFF_WARNING_THRESHOLD`: Threshold for warning about time differences

#### SingleFile Configuration
- `SINGLEFILE_EXECUTABLE_PATH`: Path to SingleFile CLI binary
- `SINGLEFILE_DATA_PATH`: Directory for storing archives
- `SINGLEFILE_TIMEOUT`: Timeout for archive operations
- `SINGLEFILE_GENERATE_SCREENSHOT`: Enable/disable screenshot generation
- `SINGLEFILE_GENERATE_PDF`: Enable/disable PDF generation
- `SINGLEFILE_SCREENSHOT_WIDTH/HEIGHT`: Screenshot dimensions

#### ArchiveBox Configuration
- `ARCHIVEBOX_BASE_URL`: Base URL for ArchiveBox API
- `ARCHIVEBOX_API_KEY`: API key for ArchiveBox authentication
- `ARCHIVEBOX_DATA_PATH`: Local path for direct file access (optional)
- `ARCHIVEBOX_EXTRACTORS`: List of extractors to use (e.g., 'singlefile,pdf')

#### Cache and Performance
- `CACHE_TTL`: Time-to-live for cache entries (seconds)
- `CACHE_MAX_ENTRIES`: Maximum number of cache entries
- `BANNER_*`: Configuration for archived page overlay banners

### Service Factory Functions
Convenience functions for service instantiation:
- `get_singlefile_manager()`: Returns SingleFileManager if configured, None otherwise
- `get_archivebox_manager()`: Returns ArchiveBoxManager if configured, None otherwise
- `get_archive_managers()`: Returns dictionary of all configured managers

### Integration with Django Models
The services integrate seamlessly with Django models:
- Use `archive.models.Shortcode` for storing archive metadata
- Use `archive.models.Visit` for tracking access analytics
- Use `accounts.models.CustomUser` for permission checking and usage limits
- Use `archive.models.ApiKey` for API authentication and rate limiting

## API

The application provides a comprehensive REST API built with Django REST Framework, replacing the original FastAPI implementation while maintaining full compatibility.

### API Structure

The API is organized into logical modules with consistent patterns:

#### Serializers (`*/serializers.py`)
Data validation and serialization using Django REST Framework serializers:
- **`AddRequestSerializer`**: Validates archive creation requests with URL, optional shortcode, and text fragment
- **`AddResponseSerializer`**: Formats archive creation responses with generated URLs and status messages
- **`ShortcodeSerializer`**: Complete shortcode details with visit counts and creator information
- **`AnalyticsResponseSerializer`**: Visit analytics with geographic and browser data
- **`CreateAPIKeyRequestSerializer`**: API key creation with usage limits and descriptions
- **`ListShortcodesResponseSerializer`**: Paginated shortcode listings with access level indicators

#### Views (`*/views.py`)
API endpoint logic using DRF APIView classes:
- **`AddArchiveView`**: POST endpoint for creating new archives (`/_add`)
- **`ListShortcodesView`**: GET endpoint for listing shortcodes with filtering (`/_shortcodes`)
- **`ShortcodeDetailView`**: GET/PUT/DELETE for individual shortcode management (`/_shortcodes/{shortcode}`)
- **`AnalyticsView`**: GET endpoint for detailed visit analytics (`/_analytics/{shortcode}`)
- **`APIKeyCreateView`**: POST endpoint for API key generation (`/_api/keys`)
- **`APIKeyUpdateView`**: PUT endpoint for API key management (`/_api/keys/{key}`)

#### Permissions (`core/permissions.py`)
Custom DRF permission classes for fine-grained access control:
- **`IsAuthenticatedWithApiKey`**: Validates API keys with usage limit checking
- **`IsMasterApiKey`**: Requires master API key for administrative operations
- **`IsMasterOrCreatorApiKey`**: Allows access with either master key or valid user API key
- **`IsOwnerOrMasterKey`**: Object-level permissions for resource owners
- **`IsPublicOrAuthenticated`**: Conditional access based on server configuration

#### URL Routing (`*/urls.py`)
RESTful URL patterns with consistent naming:
- Archive management: `/_add`, `/_shortcodes`, `/_shortcodes/{shortcode}`
- Analytics: `/_analytics/{shortcode}`
- API keys: `/_api/keys`, `/_api/keys/{key}`
- Admin: `/_health`, `/_info`, `/_cache/clear`

### API Features

#### Authentication & Authorization
- **API Key Authentication**: Bearer token authentication with usage limits
- **Master Key Access**: Administrative access for system management
- **Permission-Based Access**: Different access levels (public, creator, master)
- **Usage Tracking**: Automatic tracking of API key usage with daily/total limits

#### Archive Management
- **Flexible Archive Creation**: Support for custom shortcodes and text fragments
- **Multiple Archive Methods**: SingleFile and ArchiveBox integration
- **Duplicate Detection**: Automatic detection and handling of identical content
- **Asset Generation**: Optional favicon, screenshot, and PDF generation

#### Analytics & Reporting
- **Visit Tracking**: Detailed analytics with IP geolocation and browser detection
- **Usage Statistics**: API key usage monitoring and reporting
- **Access Control**: Owner-based access to analytics data
- **Export Capabilities**: JSON-formatted data for external analysis

#### Error Handling & Validation
- **Comprehensive Validation**: Input validation with detailed error messages
- **HTTP Status Codes**: Proper REST status codes for all operations
- **Permission Errors**: Clear error messages for authorization failures
- **Rate Limiting**: Automatic enforcement of usage limits

### API Documentation

The API includes comprehensive OpenAPI documentation:

- **Interactive Documentation**: Available at `/api/docs/` (Swagger UI)
- **Schema Download**: Available at `/api/schema/` (OpenAPI 3.0 JSON)
- **Endpoint Discovery**: Automatic schema generation from DRF serializers and views
- **Request/Response Examples**: Complete examples for all endpoints

### Migration from FastAPI

The DRF implementation maintains full compatibility with the original FastAPI endpoints:

1. **Endpoint Compatibility**: All original URLs and request/response formats preserved
2. **Authentication Parity**: Same API key validation and permission logic
3. **Business Logic**: Identical archiving and analytics functionality
4. **Error Responses**: Consistent error handling and status codes

#### Key Improvements
- **Better Serialization**: More robust data validation with DRF serializers
- **Permission System**: Cleaner, more maintainable permission classes
- **Documentation**: Automatic API documentation generation
- **Django Integration**: Native Django ORM integration and admin support
- **Testing Support**: Built-in DRF testing utilities and fixtures

### Usage Examples

#### Create Archive
```bash
curl -X POST "http://localhost:8000/api/v1/_add" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "url": "https://example.com",
    "text_fragment": "important text to highlight"
  }'
```

#### List Shortcodes
```bash
curl "http://localhost:8000/api/v1/_shortcodes?limit=10&offset=0" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Get Analytics
```bash
curl "http://localhost:8000/api/v1/_analytics/abc123" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## User Authentication

The application uses django-allauth to provide a comprehensive user authentication and account management system. All authentication endpoints are available under the `/accounts/` path.

### Authentication Features

#### Account Management
- **User Registration**: Email-based signup with email verification
- **User Login**: Secure login with session management
- **Password Reset**: Secure password reset via email
- **Email Management**: Users can manage multiple email addresses
- **Account Settings**: Profile updates and preferences

#### Security Features
- **Email Verification**: Mandatory email verification for new accounts
- **Password Validation**: Strong password requirements with Django validators
- **Session Management**: Secure session handling with configurable timeouts
- **CSRF Protection**: Built-in CSRF protection for all forms

#### User Experience
- **Modern UI**: Clean, responsive forms styled with Bootstrap 5
- **Consistent Branding**: Unified design across all authentication pages
- **Clear Navigation**: Intuitive flow between login, signup, and account management
- **Message System**: Clear feedback for user actions and errors

### Authentication Endpoints

django-allauth provides comprehensive authentication endpoints:

#### Core Authentication
- **Login**: `/accounts/login/` - User login form
- **Signup**: `/accounts/signup/` - User registration form
- **Logout**: `/accounts/logout/` - User logout confirmation
- **Password Reset**: `/accounts/password/reset/` - Request password reset
- **Password Change**: `/accounts/password/change/` - Change password (authenticated)

#### Email Management
- **Email Settings**: `/accounts/email/` - Manage email addresses
- **Email Confirmation**: `/accounts/confirm-email/{key}/` - Confirm email address
- **Email Verification**: `/accounts/verify-email/` - Request email verification

#### Account Management
- **Profile Settings**: `/accounts/profile/` - Update profile information
- **Account Settings**: `/accounts/settings/` - General account settings
- **Delete Account**: `/accounts/delete/` - Account deletion (if enabled)

### Configuration

Authentication is configured via Django settings with the following key features:

#### Login Method
- **Email-based login**: Users authenticate with email address instead of username
- **Username not required**: Simplified signup process without username selection
- **Unique email addresses**: Each email can only be associated with one account

#### Email Verification
- **Mandatory verification**: Users must verify their email before accessing the application
- **Automatic login**: Users are logged in immediately after email confirmation
- **Single-click confirmation**: Email confirmation links work with GET requests

#### User Flow
- **Redirect after login**: Users are redirected to `/dashboard/` after successful login
- **Redirect after logout**: Users are redirected to `/` after logout
- **Remember me**: Session persistence across browser sessions

### Templates

The authentication system includes professionally designed templates:

#### Template Structure
- **Base Template**: `templates/base.html` - Common layout with navigation and branding
- **Login Template**: `templates/account/login.html` - User login form
- **Signup Template**: `templates/account/signup.html` - User registration form
- **Email Confirm**: `templates/account/email_confirm.html` - Email confirmation page
- **Logout Template**: `templates/account/logout.html` - Logout confirmation
- **Password Reset**: `templates/account/password_reset.html` - Password reset form

#### Template Features
- **Bootstrap 5 Styling**: Modern, responsive design with consistent branding
- **Crispy Forms**: Enhanced form rendering with proper validation display
- **Mobile Responsive**: Optimized for all device sizes
- **Accessibility**: Proper ARIA labels and keyboard navigation
- **Loading States**: Visual feedback during form submission

### User Model

The application uses a custom user model (`accounts.CustomUser`) with additional fields:

#### Core Fields
- **email**: Primary identifier (replaces username)
- **display_name**: User's preferred display name
- **first_name** / **last_name**: Optional personal information
- **is_active** / **is_staff** / **is_superuser**: Standard Django permissions

#### Citis-Specific Fields
- **default_archive_method**: User's preferred archiving method
- **is_premium**: Premium subscription status
- **monthly_shortcode_limit**: Monthly usage limit for shortcode creation
- **created_at** / **updated_at**: Timestamp tracking

### Integration with Core Features

#### API Authentication
- **Session Authentication**: Web interface uses Django sessions
- **API Key Authentication**: Programmatic access via API keys
- **Permission Integration**: User permissions control API access levels

#### Dashboard Access
- **Authenticated Routes**: Login required for dashboard and account management
- **User-Specific Data**: Shortcodes and analytics filtered by user ownership
- **Usage Tracking**: Monthly limits and usage statistics per user

#### Email Notifications
- **Welcome Emails**: Automated welcome email after registration
- **Password Reset**: Secure password reset emails
- **Account Notifications**: Updates on account changes and security events

### Development Configuration

For development, the authentication system is configured with:

#### Email Backend
- **Console Backend**: Email confirmations printed to console during development
- **No SMTP Required**: Development setup works without email server
- **Test Email Addresses**: Use any email address for testing

#### Security Settings
- **Debug Mode**: Enhanced error messages and debugging information
- **Relaxed Validation**: Simplified password requirements for development
- **Local Sessions**: Session data stored locally for development

### Future Enhancements

Planned authentication features include:

#### Social Authentication
- **GitHub Integration**: Login with GitHub account
- **Google Integration**: Login with Google account
- **Provider Management**: Support for additional OAuth providers

#### Two-Factor Authentication
- **TOTP Support**: Time-based one-time passwords
- **SMS Integration**: SMS-based verification
- **Recovery Codes**: Backup authentication methods

#### Team Management
- **Organization Accounts**: Team-based account management
- **Role-Based Access**: Different permission levels within teams
- **Invitation System**: Invite users to join organizations

## Admin Interface

Citis includes a comprehensive Django admin interface for system administration and data management. The admin panel provides powerful tools for managing all aspects of the application.

### Accessing the Admin Interface

The admin interface is available at `/admin/` and requires a superuser account. To create an administrator account:

```bash
python manage.py createsuperuser
```

Follow the prompts to set up your administrator credentials. Once created, you can access the admin panel by navigating to `/admin/` and logging in with your superuser credentials.

### Admin Features

The admin interface provides comprehensive management tools for all core data models:

#### User Management
- **User Accounts**: View, edit, and manage all user accounts
- **Premium Status**: Upgrade users to premium or modify subscription details
- **Usage Monitoring**: Track monthly archive creation and API usage
- **Account Activity**: Monitor login patterns and account status
- **API Key Management**: View and manage user API keys directly from user profiles

#### Archive Management
- **Shortcode Administration**: View, edit, and manage all archived URLs
- **Archive Status**: Monitor archiving progress and troubleshoot failed archives
- **Content Analysis**: Review text fragments and archive metadata
- **Creator Tracking**: Identify who created each archive and when
- **Direct Access**: Quick links to view archived content from the admin interface

#### Analytics & Monitoring
- **Visit Tracking**: Comprehensive analytics for all archive access
- **Geographic Analysis**: Monitor access patterns by country and region
- **Browser Analytics**: Track client information and user agent data
- **Time-based Reports**: Filter visits by date ranges and time periods
- **IP Analysis**: Monitor access patterns and identify potential issues

#### API Key Administration
- **Usage Monitoring**: Track API key usage against daily and total limits
- **Access Control**: Activate, deactivate, or modify API key permissions
- **Security Management**: Monitor API key creation and last usage dates
- **Bulk Operations**: Manage multiple API keys efficiently

### Admin Interface Customization

The admin interface includes several enhanced features:

- **Advanced Filtering**: Filter records by dates, users, status, and archive methods
- **Search Functionality**: Search across URLs, shortcodes, email addresses, and other key fields
- **Batch Operations**: Perform bulk actions on multiple records simultaneously
- **Related Object Management**: Manage related records (API keys, visits) directly from parent objects
- **Visual Indicators**: Color-coded status indicators and usage statistics
- **Direct Links**: Quick access to archived content and external resources

### Security Considerations

- Admin access is restricted to superuser accounts only
- All admin actions are logged for audit purposes
- Sensitive data (like full API keys) is partially masked for security
- Visit data is read-only to preserve analytics integrity

The admin interface is designed to be both powerful for system administrators and safe for day-to-day operations.

## Web Interface

The application features a comprehensive web interface built with Django templates, Bootstrap 5, and HTMX for dynamic interactions. The interface provides both marketing pages and a full-featured user dashboard.

### Frontend Stack

- **Django Templates**: Server-side rendering with template inheritance
- **Bootstrap 5**: Modern, responsive CSS framework with custom theming
- **HTMX**: Dynamic content updates without full page reloads
- **Chart.js**: Interactive charts for analytics visualization
- **Bootstrap Icons**: Comprehensive icon library for UI elements

### Page Structure

#### Marketing Pages (`web/views.py`)
- **Landing Page** (`/`): Hero section, features overview, statistics, and call-to-action
- **Pricing Page** (`/pricing/`): Three-tier pricing with FAQ accordion
- **About Page** (`/about/`): Mission, features, and company information

#### Dashboard Pages (Authenticated)
- **Dashboard** (`/dashboard/`): User overview with statistics, recent archives, and API key management
- **My Archives** (`/shortcodes/`): Paginated list of user's archives with search functionality
- **Archive Details** (`/shortcodes/{shortcode}/`): Individual archive analytics and management
- **Create Archive** (`/create/`): Form for creating new archives with usage limits

#### Authentication Pages
- **Login** (`/accounts/login/`): User authentication form
- **Signup** (`/accounts/signup/`): User registration form
- **Password Reset**: Secure password reset workflow

### Template Architecture

#### Base Template (`templates/base.html`)
- **Bootstrap 5 Integration**: CDN-loaded Bootstrap with custom CSS variables
- **Responsive Navigation**: Collapsible navbar with authentication-aware menu
- **HTMX Integration**: Dynamic content loading and form submissions
- **Custom Branding**: Configurable colors and styling
- **Footer**: Links, branding, and company information

#### Template Features
- **Template Inheritance**: DRY principle with base template and blocks
- **Responsive Design**: Mobile-first approach with Bootstrap grid system
- **Accessibility**: ARIA labels, keyboard navigation, and semantic HTML
- **Loading States**: Visual feedback during form submissions and HTMX requests
- **Error Handling**: Comprehensive error displays and user feedback

### Dashboard Components

#### Statistics Cards
- **Monthly Archives**: User's archives created this month
- **Total Archives**: Lifetime archive count
- **Total Views**: Aggregate view count across all archives
- **Active API Keys**: Number of active API keys

#### Recent Archives Table
- **Archive Information**: URL, shortcode, creation date, and view count
- **Text Fragments**: Display of highlighted text passages
- **Quick Actions**: Copy shortcode, view archive, and access details

#### API Key Management
- **HTMX-Powered**: Dynamic key creation, updating, and deletion
- **Key Details**: Name, status, creation date, and usage information
- **Copy Functionality**: One-click API key copying with toast notifications
- **Inline Editing**: Edit key names and status without page reload

#### Activity Charts
- **Chart.js Integration**: Interactive charts for view analytics
- **Time-based Views**: Daily, weekly, and monthly activity patterns
- **Responsive Charts**: Automatic resizing for different screen sizes

### Dynamic Features (HTMX)

#### API Key Management
- **Create Keys**: Modal form for new API key creation
- **Update Keys**: Inline editing with immediate feedback
- **Delete Keys**: Confirmation dialog with immediate removal
- **Real-time Updates**: No page reloads for key management operations

#### Archive Management
- **Search**: Real-time search filtering of archive list
- **Pagination**: HTMX-powered pagination without page reloads
- **Bulk Actions**: Select multiple archives for batch operations

#### Form Enhancements
- **Validation**: Real-time form validation with error display
- **Progress Indicators**: Loading states for long-running operations
- **Toast Notifications**: Success and error messages with auto-dismiss

### URL Configuration (`web/urls.py`)

#### Marketing Routes
- `/` → Landing page with site overview
- `/pricing/` → Pricing tiers and FAQ
- `/about/` → About page and company information

#### Dashboard Routes
- `/dashboard/` → Main user dashboard
- `/shortcodes/` → Archive list with search and pagination
- `/shortcodes/{shortcode}/` → Individual archive details and analytics
- `/create/` → Archive creation form with usage limits

#### HTMX Endpoints
- `/api-keys/create/` → Create new API key
- `/api-keys/{id}/update/` → Update existing API key
- `/api-keys/{id}/delete/` → Delete API key

### User Experience Features

#### Navigation
- **Authenticated Menu**: Different navigation for logged-in users
- **Breadcrumbs**: Clear navigation hierarchy on detail pages
- **Search**: Global search functionality across archives

#### Responsive Design
- **Mobile-First**: Optimized for mobile devices with touch-friendly interactions
- **Tablet Support**: Optimal layout for tablet viewing
- **Desktop Enhancement**: Full-featured desktop experience

#### Performance
- **Template Caching**: Efficient template rendering with Django cache
- **Asset Optimization**: Minified CSS and JavaScript for production
- **Lazy Loading**: Progressive loading of non-critical content

### Accessibility Features

#### WCAG Compliance
- **Semantic HTML**: Proper use of headings, lists, and form elements
- **ARIA Labels**: Screen reader support for dynamic content
- **Keyboard Navigation**: Full keyboard accessibility
- **Color Contrast**: High contrast design for readability

#### User Assistance
- **Form Help Text**: Clear instructions for all form fields
- **Error Messages**: Descriptive error messages with recovery suggestions
- **Loading Indicators**: Visual feedback for all asynchronous operations

### Customization

#### Theming
- **CSS Variables**: Easy color and spacing customization
- **Bootstrap Overrides**: Custom Bootstrap variable overrides
- **Brand Colors**: Consistent color scheme across all pages

#### Content Management
- **Dynamic Content**: Database-driven content for statistics and features
- **Template Blocks**: Extensible template structure for customization
- **Localization Ready**: Template structure supports future i18n

### Integration with Backend

#### Django Integration
- **Template Context**: Rich context data from Django views
- **Form Handling**: Django forms with crispy forms styling
- **Message Framework**: Django messages for user feedback
- **Permission System**: Template-level permission checking

#### API Integration
- **HTMX Endpoints**: Seamless integration with Django REST Framework
- **Authentication**: Session-based authentication for web interface
- **Error Handling**: Consistent error handling across web and API

## Development Status

This project is currently being refactored from a FastAPI-based implementation to a full-featured Django SaaS application. The migration includes:

- ✅ **Step 1: Project Scaffolding** - Django project and app structure created
- ✅ **Step 2: Configuration** - Django settings and environment management
- ✅ **Step 3: Database Modeling** - Django ORM model definitions and migrations
- ✅ **Step 4: Data Migration** - Legacy FastAPI data successfully migrated to Django models
- ✅ **Step 5: Service Integration** - Core business logic services integrated and configured
- ✅ **Step 6: API Refactoring** - Django REST Framework API endpoints implemented
- ✅ **Step 7: Authentication** - User account system with django-allauth
- ✅ **Step 8: Web UI** - Django template-based frontend with Bootstrap 5 and HTMX
- ✅ **Step 9: Admin Setup** - Comprehensive Django admin interface with enhanced features
- ⏳ **Step 10: Testing** - Test suite migration

## Quick Start

*Note: Full setup instructions will be added as the project progresses through the refactoring steps.*

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd citis
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment setup**
   ```bash
   # Copy the environment template and configure your settings
   cp .env.example .env
   # Edit .env with your specific configuration values
   ```

4. **Database setup**
   ```bash
   python manage.py migrate
   ```

5. **Run development server**
   ```bash
   python manage.py runserver
   ```

## Key Features

### For End Users
- Create permanent archives of any web page
- Generate short, permanent URLs for citation
- Highlight specific text passages for precise referencing
- Access detailed analytics on archive usage
- Team collaboration and sharing features

### For Developers
- RESTful API for programmatic access
- Webhook support for integrations
- Bulk archiving capabilities
- Custom branding and white-label options

### For Organizations
- Team management and access controls
- Usage analytics and reporting
- Custom retention policies
- Enterprise-grade reliability

## Contributing

This project is currently in active development as part of a FastAPI-to-Django migration. Contribution guidelines will be established once the core refactoring is complete.

## License

*License information to be added*

---

*This README will be updated as each step of the Django migration is completed.* 
