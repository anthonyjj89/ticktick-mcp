# Changelog

All notable changes to the TickTick MCP Server will be documented in this file.

## [1.5.0] - 2024-05-07

### Added
- Enhanced Tag Support: Added `tags` parameter to create_task and update_task functions
- Batch Task Creation: New create_tasks function for creating multiple tasks at once
- Smart Tag Handling: Intelligent extraction and preservation of existing tags during updates
- Tag Deduplication: Automatic handling of duplicate tags for cleaner task titles

### Changed
- Improved documentation with detailed examples for tags and batch operations
- Enhanced error handling for batch operations with detailed success/failure reporting
- Implemented intelligent tag extraction from existing task titles during updates
- Added support for TickTick's batch API endpoints with graceful fallback to individual operations

## [1.4.0] - 2024-05-07

### Added
- Improved task deletion verification with project listing checks
- Added delay mechanism for API backend sync verification
- Added informational notices about sync delays instead of error messages

### Changed
- Updated task deletion error handling to handle TickTick API sync delays
- Fixed issue with task deletion verification showing false errors
- Changed error messages (❌) to informational notices (ℹ️) for sync-related issues
- Added consistent messaging between client and server layers
- Updated client-level error messages to align with server-level approach

### Fixed
- Fix task deletion verification that incorrectly reported errors due to API caching
- Fix error messages consistency across client and server layers
- Better handling of TickTick's API behavior where deleted tasks may still be accessible via direct lookup

## [1.3.0] - 2024-04-15

### Added
- Enhanced task and project display with visually distinct ID sections
- Added reference information sections for easy copying of task/project IDs
- Added comprehensive error handling for all API operations
- Added verification steps for all CRUD operations
- Added rate limit handling with retry functionality

### Changed
- Fixed update_task method to properly preserve all existing task data
- Improved error messages with visual indicators, error codes, and helpful descriptions
- Enhanced all operations with pre and post-operation verification
- Added detailed operation feedback with clear success/error indicators

## [1.2.0] - 2024-03-10

### Added
- New `list_all_tasks` function to quickly find task IDs across all projects
- New `find_old_tasks` function to identify stale tasks for maintenance
- Added verification steps to ensure operation success

### Changed
- Improved task identification with prominent ID display
- Enhanced error message responses for troubleshooting
- Better error handling and verification for all CRUD operations
- Improved API integration with enhanced error handling and response validation

## [1.1.0] - 2024-02-20

### Added
- Support for recurring tasks with customizable patterns
- Support for RRULE format for recurring task definition