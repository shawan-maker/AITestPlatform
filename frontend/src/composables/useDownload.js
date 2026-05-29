export function useDownload() {
  function downloadBlob(blob, filename = 'download') {
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  async function downloadFromResponse(response, fallbackName = 'download') {
    const disposition = response.headers?.['content-disposition'] || ''
    const match = disposition.match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i)
    const filename = match ? decodeURIComponent(match[1].replace(/"/g, '')) : fallbackName
    downloadBlob(response.data, filename)
  }

  function downloadJson(data, filename = 'data.json') {
    const name = filename.endsWith('.json') ? filename : `${filename}.json`
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    downloadBlob(blob, name)
  }

  return { downloadBlob, downloadFromResponse, downloadJson }
}
