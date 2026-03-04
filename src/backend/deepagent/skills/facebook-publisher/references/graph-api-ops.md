# Facebook Graph API Ops (Adapted)

Source adapted from imported `facebook-page-manager-1.0.0` references.

## Base
- Graph API base: `https://graph.facebook.com/v21.0`

## Key operations
- List managed pages: `GET /me/accounts`
- Create text/link post: `POST /{page-id}/feed`
- Create photo post: `POST /{page-id}/photos`
- List comments: `GET /{post-id}/comments`
- Reply comment: `POST /{comment-id}/comments`

## Permissions mapping
- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_posts`
- `pages_manage_engagement`

## Guardrails
- Never log tokens.
- Keep publish action approval-gated.
- Prefer scheduled/draft path before immediate publish.
