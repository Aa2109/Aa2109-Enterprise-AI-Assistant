import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { listDocuments, uploadDocument } from '@/lib/api/documents.api'
import type { DocumentResponse } from '@/lib/api/types'

export const documentKeys = {
  all: ['documents'] as const,
}

export function useDocuments() {
  // While any document is still processing, poll so the status row
  // advances to READY on its own.
  return useQuery({
    queryKey: documentKeys.all,
    queryFn: listDocuments,
    staleTime: 10_000,
    refetchInterval: (query) => {
      const docs = query.state.data as DocumentResponse[] | undefined
      const processing = docs?.some(
        (doc) => doc.status === 'UPLOADED' || doc.status === 'EXTRACTING' || doc.status === 'EXTRACTED' || doc.status === 'CHUNKING',
      )
      return processing ? 5000 : false
    },
  })
}

export function useUploadDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: documentKeys.all }),
  })
}