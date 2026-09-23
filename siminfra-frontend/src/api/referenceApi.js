import apiClient from './client';


const pendingRequests = new Map();

export const getReferenceData = (sections = []) => {
  const normalizedSections = [...sections].sort();
  const key = normalizedSections.join(',') || 'all';

  if (pendingRequests.has(key)) {
    return pendingRequests.get(key);
  }

  const request = apiClient.get('/reference-data/', {
    params: normalizedSections.length
      ? { include: normalizedSections.join(',') }
      : {},
  })
    .then((response) => response.data)
    .finally(() => pendingRequests.delete(key));

  pendingRequests.set(key, request);
  return request;
};
