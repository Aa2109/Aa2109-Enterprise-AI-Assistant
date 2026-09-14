import { api } from './client'
import type { DocumentResponse } from './types'

export function listDocuments(): Promise<DocumentResponse[]> {
  return api<DocumentResponse[]>('/documents')
}

/** Multipart upload — the browser sets the Content-Type boundary. */
export function uploadDocument(file: File): Promise<DocumentResponse> {
  const formData = new FormData()
  formData.append('file', file)
  return api<DocumentResponse>('/documents/upload', { method: 'POST', formData })
}