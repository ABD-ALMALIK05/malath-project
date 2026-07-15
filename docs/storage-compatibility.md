# Storage Compatibility Notes

Malath now treats `Document.stored_filename` as the private storage key used by both
local storage and S3. The model exposes this value through the `storage_key`
property so new code does not depend on permanent public file URLs.

The existing `file_url` database column is intentionally preserved for legacy
records. New uploads store the same private storage key in `file_url` only as
backward-compatible metadata; download behavior uses the authenticated
`/documents/download/<id>` route.

No schema migration is required for this storage change because the existing
columns are retained. Existing records should continue to download when
`stored_filename` contains the object key originally used for the upload.
