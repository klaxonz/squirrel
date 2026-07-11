import { get } from '@/shared/lib/request'
import type { CreatorDetail } from '@/features/video/types/creator'

export const getCreatorDetail = async (creatorId: string | number) => {
  return get<CreatorDetail>(`/api/creator/detail/${creatorId}`)
}
