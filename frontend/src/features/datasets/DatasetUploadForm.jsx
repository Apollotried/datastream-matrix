import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import {
  getDatasetsListQueryKey,
  useDatasetsUploadCreate,
} from '../../api/generated/datastream-matrix'

function getErrorMessage(error) {
  return error?.body?.error?.message ?? error?.message ?? 'Upload failed'
}

export function DatasetUploadForm() {
  const queryClient = useQueryClient()
  const [selectedFile, setSelectedFile] = useState(null)
  const uploadMutation = useDatasetsUploadCreate({
    mutation: {
      onSuccess: () => {
        setSelectedFile(null)
        queryClient.invalidateQueries({
          queryKey: getDatasetsListQueryKey(),
        })
      },
    },
  })

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] ?? null
    setSelectedFile(file)
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    if (!selectedFile) {
      return
    }

    uploadMutation.mutate({
      data: {
        file: selectedFile,
      },
    })
  }

  return (
    <form onSubmit={handleSubmit} className="upload-form">
      <label>
        CSV file
        <input type="file" accept=".csv" onChange={handleFileChange} />
      </label>

      {selectedFile ? (
        <p className="muted">Selected: {selectedFile.name}</p>
      ) : null}

      {uploadMutation.isError ? (
        <p role="alert" className="error">
          {getErrorMessage(uploadMutation.error)}
        </p>
      ) : null}

      {uploadMutation.isSuccess ? (
        <p className="success">Upload created. Processing will run in Celery.</p>
      ) : null}

      <button type="submit" disabled={!selectedFile || uploadMutation.isPending}>
        {uploadMutation.isPending ? 'Uploading...' : 'Upload dataset'}
      </button>
    </form>
  )
}
