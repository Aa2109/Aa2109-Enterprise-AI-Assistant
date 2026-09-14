import { useRef, useState } from 'react'
import { FileText, RefreshCw, FileUp } from 'lucide-react'
import { toast } from 'sonner'

import { useDocuments, useUploadDocument } from './useDocuments'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'
import {
  DOCUMENT_STATUS_LABEL,
  DOCUMENT_STATUS_TONE,
  formatDateTime,
} from '@/lib/format'

export function DocumentsPage() {
  const { data, isLoading, refetch, isFetching } = useDocuments()
  const upload = useUploadDocument()
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragOver, setIsDragOver] = useState(false)

  const handleFile = async (file?: File | null) => {
    if (!file) return
    try {
      await upload.mutateAsync(file)
      toast.success('Uploaded — processing started')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload failed'
      toast.error(message)
    } finally {
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-fg">Documents</h2>
          <p className="text-sm text-fg-muted">
            Upload files to build your internal knowledge base. They are
            chunked, embedded, and made searchable for the RAG agent.
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={`size-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(event) => {
          event.preventDefault()
          setIsDragOver(true)
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(event) => {
          event.preventDefault()
          setIsDragOver(false)
          handleFile(event.dataTransfer.files?.[0])
        }}
        onClick={() => inputRef.current?.click()}
        className={`mb-6 flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-6 py-8 transition-colors ${
          isDragOver
            ? 'border-accent bg-accent-dim'
            : 'border-edge bg-surface hover:border-accent/40'
        }`}
      >
        <div className="flex size-10 items-center justify-center rounded-full bg-elevated text-accent-strong">
          <FileUp className="size-5" />
        </div>
        <p className="text-sm font-medium text-fg">
          {upload.isPending ? 'Uploading…' : 'Click to upload or drag a file here'}
        </p>
        <p className="text-xs text-fg-faint">
          PDF · DOCX · TXT · MD — processed in the background
        </p>
        <input
          ref={inputRef}
          type="file"
          hidden
          onChange={(event) => handleFile(event.target.files?.[0])}
        />
      </div>

      {/* List */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : data?.length === 0 ? (
        <Card>
          <EmptyState
            icon={<FileText className="size-6" />}
            title="No documents yet"
            description="Upload a policy, handbook, or report and the RAG agent will be able to ground answers in it."
          />
        </Card>
      ) : (
        <ul className="space-y-2">
          {data?.map((document) => (
            <li key={document.id}>
              <Card className="flex items-center gap-3 px-4 py-3">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-elevated text-accent-strong">
                  <FileText className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-fg">
                    {document.original_filename}
                  </p>
                  <p className="text-xs text-fg-faint">
                    {formatDateTime(document.created_at)}
                  </p>
                </div>
                <Badge tone={DOCUMENT_STATUS_TONE[document.status]} >
                  {DOCUMENT_STATUS_LABEL[document.status]}
                </Badge>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}