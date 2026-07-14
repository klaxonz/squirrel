// DTOs for /api/users/* — field shapes mirror the backend User model.
// See backend: domains/user/domain/models/user.py (User.to_dict, token_version excluded)
//
// Note: backend NEVER returns email on these endpoints. The frontend User type
// previously declared `email?` and read undefined.

export interface User {
  id: number | string
  nickname: string
  avatar: string | null
  created_at: string
  updated_at: string
}

/** GET /api/users/me/config — partial settings dict. */
export interface UserConfig {
  showNsfw?: boolean
  autoplay?: boolean
  autoplayNext?: boolean
  loop?: boolean
}
