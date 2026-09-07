import { useDeferredValue, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  useDatasetsErrorsList,
  useDatasetsRecordsList,
  useDatasetsStatusRetrieve,
} from '../../api/generated/datastream-matrix'

function getErrorMessage(error) {
  return error?.body?.error?.message ?? error?.message ?? 'Request failed'
}

function getRows(response) {
  const payload = response?.data

  if (Array.isArray(payload)) {
    return payload
  }

  return payload?.results ?? []
}

function isProcessingStatus(status) {
  return status === 'PENDING' || status === 'PROCESSING'
}

export function DatasetDetailPage() {
  const { datasetId } = useParams()
  const [customerEmailFilter, setCustomerEmailFilter] = useState('')
  const [purchasedAtFromFilter, setPurchasedAtFromFilter] = useState('')
  const [purchasedAtToFilter, setPurchasedAtToFilter] = useState('')
  const deferredCustomerEmailFilter = useDeferredValue(customerEmailFilter)

  const statusQuery = useDatasetsStatusRetrieve(datasetId, {
    query: {
      refetchInterval: (query) => {
        const status = query.state.data?.data?.status

        return isProcessingStatus(status) ? 1000 : false
      },
    },
  })

  const dataset = statusQuery.data?.data
  const canLoadRows = dataset?.status === 'COMPLETED'
  const recordParams = {
    ...(deferredCustomerEmailFilter.trim()
      ? { customer_email: deferredCustomerEmailFilter.trim() }
      : {}),
    ...(purchasedAtFromFilter
      ? { purchased_at_from: purchasedAtFromFilter }
      : {}),
    ...(purchasedAtToFilter ? { purchased_at_to: purchasedAtToFilter } : {}),
  }
  const recordsQuery = useDatasetsRecordsList(datasetId, recordParams, {
    query: {
      enabled: Boolean(datasetId) && canLoadRows,
    },
  })
  const errorsQuery = useDatasetsErrorsList(datasetId, {
    query: {
      enabled: Boolean(datasetId) && canLoadRows,
    },
  })
  const records = getRows(recordsQuery.data)
  const rowErrors = getRows(errorsQuery.data)
  const hasRecordFilters = Boolean(
    customerEmailFilter || purchasedAtFromFilter || purchasedAtToFilter,
  )

  const clearRecordFilters = () => {
    setCustomerEmailFilter('')
    setPurchasedAtFromFilter('')
    setPurchasedAtToFilter('')
  }

  return (
    <main className="app-shell">
      <Link to="/datasets" className="back-link">
        Back to datasets
      </Link>

      <section className="content-card detail-card">
        <h1>Dataset details</h1>

        {statusQuery.isLoading ? (
          <p className="muted">Loading status...</p>
        ) : null}

        {statusQuery.isError ? (
          <p role="alert" className="error">
            {getErrorMessage(statusQuery.error)}
          </p>
        ) : null}

        {dataset ? (
          <div className="detail-grid">
            <div>
              <span>Status</span>
              <strong>{dataset.status}</strong>
            </div>
            <div>
              <span>Total rows</span>
              <strong>{dataset.total_rows}</strong>
            </div>
            <div>
              <span>Processed</span>
              <strong>{dataset.processed_rows}</strong>
            </div>
            <div>
              <span>Failed</span>
              <strong>{dataset.failed_rows}</strong>
            </div>
          </div>
        ) : null}

        {dataset && isProcessingStatus(dataset.status) ? (
          <p className="muted">Checking progress every second...</p>
        ) : null}
      </section>

      <section className="content-card detail-card">
        <h2>Valid records</h2>

        <div className="filters record-filters">
          <label>
            Customer email
            <input
              type="search"
              value={customerEmailFilter}
              onChange={(event) => setCustomerEmailFilter(event.target.value)}
              placeholder="alice@example.com"
              disabled={!canLoadRows}
            />
          </label>

          <label>
            Purchased from
            <input
              type="date"
              value={purchasedAtFromFilter}
              onChange={(event) =>
                setPurchasedAtFromFilter(event.target.value)
              }
              disabled={!canLoadRows}
            />
          </label>

          <label>
            Purchased to
            <input
              type="date"
              value={purchasedAtToFilter}
              onChange={(event) => setPurchasedAtToFilter(event.target.value)}
              disabled={!canLoadRows}
            />
          </label>

          <button
            type="button"
            className="secondary-button"
            onClick={clearRecordFilters}
            disabled={!hasRecordFilters}
          >
            Clear filters
          </button>
        </div>

        {!canLoadRows ? (
          <p className="muted">Records will load after processing completes.</p>
        ) : null}

        {recordsQuery.isLoading ? (
          <p className="muted">Loading records...</p>
        ) : null}

        {recordsQuery.isError ? (
          <p role="alert" className="error">
            {getErrorMessage(recordsQuery.error)}
          </p>
        ) : null}

        {records.length === 0 && recordsQuery.isSuccess ? (
          <p className="muted">No valid records found.</p>
        ) : null}

        {records.length > 0 ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Row</th>
                  <th>Email</th>
                  <th>Product</th>
                  <th>Quantity</th>
                  <th>Unit price</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <tr key={record.id}>
                    <td>{record.row_number}</td>
                    <td>{record.customer_email}</td>
                    <td>{record.product_name}</td>
                    <td>{record.quantity}</td>
                    <td>{record.unit_price}</td>
                    <td>{record.purchased_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="content-card detail-card">
        <h2>Invalid rows</h2>

        {errorsQuery.isLoading ? (
          <p className="muted">Loading errors...</p>
        ) : null}

        {errorsQuery.isError ? (
          <p role="alert" className="error">
            {getErrorMessage(errorsQuery.error)}
          </p>
        ) : null}

        {!canLoadRows ? (
          <p className="muted">Errors will load after processing completes.</p>
        ) : null}

        {rowErrors.length === 0 && errorsQuery.isSuccess ? (
          <p className="muted">No invalid rows found.</p>
        ) : null}

        {rowErrors.length > 0 ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Row</th>
                  <th>Errors</th>
                  <th>Raw data</th>
                </tr>
              </thead>
              <tbody>
                {rowErrors.map((rowError) => (
                  <tr key={`${rowError.dataset_id}-${rowError.row_number}`}>
                    <td>{rowError.row_number}</td>
                    <td>{rowError.errors.join(', ')}</td>
                    <td>
                      <code>{JSON.stringify(rowError.raw_data)}</code>
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
