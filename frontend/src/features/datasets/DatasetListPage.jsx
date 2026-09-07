import { useDeferredValue, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import {
  datasetsExportRetrieve,
  getDatasetsListQueryKey,
  useDatasetsList,
  useDatasetsRetryCreate,
} from '../../api/generated/datastream-matrix'
import { useAuth } from '../../auth/useAuth'
import { DatasetUploadForm } from './DatasetUploadForm.jsx'

function getErrorMessage(error) {
  return error?.body?.error?.message ?? error?.message ?? 'Could not load datasets'
}

function getDatasetRows(response) {
  const payload = response?.data

  if (Array.isArray(payload)) {
    return payload
  }

  return payload?.results ?? []
}

function getDatasetCount(response, rows) {
  const payload = response?.data

  if (Array.isArray(payload)) {
    return rows.length
  }

  return payload?.count ?? rows.length
}

function isProcessingStatus(status) {
  return status === 'PENDING' || status === 'PROCESSING'
}

function canRetryStatus(status) {
  return status === 'PENDING' || status === 'FAILED'
}

function canExportStatus(status) {
  return status === 'COMPLETED'
}

function hasProcessingDatasets(response) {
  return getDatasetRows(response).some((dataset) =>
    isProcessingStatus(dataset.status),
  )
}

function formatDate(value) {
  return new Intl.DateTimeFormat('en', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function DatasetListPage() {
  const queryClient = useQueryClient()
  const { logout } = useAuth()
  const [statusFilter, setStatusFilter] = useState('')
  const [searchFilter, setSearchFilter] = useState('')
  const [retryingDatasetId, setRetryingDatasetId] = useState(null)
  const [exportingDatasetId, setExportingDatasetId] = useState(null)
  const [exportError, setExportError] = useState('')
  const deferredSearchFilter = useDeferredValue(searchFilter)
  const datasetParams = {
    ...(statusFilter ? { status: statusFilter } : {}),
    ...(deferredSearchFilter.trim()
      ? { search: deferredSearchFilter.trim() }
      : {}),
  }
  const datasetsQuery = useDatasetsList(datasetParams, {
    query: {
      refetchInterval: (query) =>
        hasProcessingDatasets(query.state.data) ? 1000 : false,
    },
  })
  const rows = getDatasetRows(datasetsQuery.data)
  const count = getDatasetCount(datasetsQuery.data, rows)
  const hasFilters = Boolean(statusFilter || searchFilter)
  const retryMutation = useDatasetsRetryCreate({
    mutation: {
      onSettled: () => {
        setRetryingDatasetId(null)
      },
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: getDatasetsListQueryKey(datasetParams),
        })
      },
    },
  })

  const clearFilters = () => {
    setStatusFilter('')
    setSearchFilter('')
  }

  const handleRetry = (datasetId) => {
    setRetryingDatasetId(datasetId)
    retryMutation.mutate({ datasetId })
  }

  const handleExport = async (datasetId) => {
    setExportingDatasetId(datasetId)
    setExportError('')

    try {
      const response = await datasetsExportRetrieve(datasetId)
      const downloadUrl = URL.createObjectURL(response.data)
      const link = document.createElement('a')

      link.href = downloadUrl
      link.download = `dataset-${datasetId}-report.xlsx`
      link.click()
      URL.revokeObjectURL(downloadUrl)
    } catch (error) {
      setExportError(getErrorMessage(error))
    } finally {
      setExportingDatasetId(null)
    }
  }

  return (
    <main className="app-shell">
      <header className="toolbar">
        <div>
          <p className="eyebrow">Protected area</p>
          <h1>Datasets</h1>
        </div>

        <button type="button" className="secondary-button" onClick={logout}>
          Logout
        </button>
      </header>

      <section className="content-card upload-card">
        <div className="section-header">
          <div>
            <h2>Upload CSV</h2>
            <p>Choose a CSV file and send it to the ingestion pipeline.</p>
          </div>
        </div>

        <DatasetUploadForm />
      </section>

      <section className="content-card">
        <div className="section-header">
          <div>
            <h2>Upload history</h2>
            <p>{count} dataset job{count === 1 ? '' : 's'} found.</p>
            {hasProcessingDatasets(datasetsQuery.data) ? (
              <p className="muted">Checking active jobs every second...</p>
            ) : null}
          </div>

          <button
            type="button"
            className="secondary-button"
            onClick={() => datasetsQuery.refetch()}
            disabled={datasetsQuery.isFetching}
          >
            {datasetsQuery.isFetching ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        <div className="filters">
          <label>
            Search filename
            <input
              type="search"
              value={searchFilter}
              onChange={(event) => setSearchFilter(event.target.value)}
              placeholder="sales"
            />
          </label>

          <label>
            Status
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="">All statuses</option>
              <option value="PENDING">Pending</option>
              <option value="PROCESSING">Processing</option>
              <option value="COMPLETED">Completed</option>
              <option value="FAILED">Failed</option>
            </select>
          </label>

          <button
            type="button"
            className="secondary-button"
            onClick={clearFilters}
            disabled={!hasFilters}
          >
            Clear filters
          </button>
        </div>

        {datasetsQuery.isLoading ? (
          <p className="muted">Loading datasets...</p>
        ) : null}

        {datasetsQuery.isError ? (
          <p role="alert" className="error">
            {getErrorMessage(datasetsQuery.error)}
          </p>
        ) : null}

        {retryMutation.isError ? (
          <p role="alert" className="error">
            {getErrorMessage(retryMutation.error)}
          </p>
        ) : null}

        {exportError ? (
          <p role="alert" className="error">
            {exportError}
          </p>
        ) : null}

        {datasetsQuery.isSuccess && rows.length === 0 ? (
          <p className="muted">No datasets yet. Upload one from the API first.</p>
        ) : null}

        {rows.length > 0 ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Status</th>
                  <th>Rows</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((dataset) => (
                  <tr key={dataset.id}>
                    <td>
                      <strong>
                        <Link to={`/datasets/${dataset.id}`}>
                          {dataset.original_filename}
                        </Link>
                      </strong>
                      <span>{dataset.id}</span>
                    </td>
                    <td>
                      <span className={`status-pill ${dataset.status.toLowerCase()}`}>
                        {dataset.status}
                      </span>
                    </td>
                    <td>
                      {dataset.processed_rows}/{dataset.total_rows}
                      {dataset.failed_rows > 0 ? (
                        <span className="failed-rows">
                          {dataset.failed_rows} failed
                        </span>
                      ) : null}
                    </td>
                    <td>{formatDate(dataset.created_at)}</td>
                    <td>
                      <div className="row-actions">
                        <button
                          type="button"
                          className="secondary-button compact-button"
                          onClick={() => handleRetry(dataset.id)}
                          disabled={
                            !canRetryStatus(dataset.status) ||
                            retryMutation.isPending
                          }
                        >
                          {retryingDatasetId === dataset.id
                            ? 'Retrying...'
                            : 'Retry'}
                        </button>
                        <button
                          type="button"
                          className="secondary-button compact-button"
                          onClick={() => handleExport(dataset.id)}
                          disabled={
                            !canExportStatus(dataset.status) ||
                            exportingDatasetId === dataset.id
                          }
                        >
                          {exportingDatasetId === dataset.id
                            ? 'Exporting...'
                            : 'Export'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </main>
  )
}
