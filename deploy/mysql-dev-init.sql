-- Ensures the dev database matches production charset (runs once on first container start).
ALTER DATABASE track_maintenance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
