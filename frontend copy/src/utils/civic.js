// Minimal civic utilities to make the frontend runnable without Base44.
export function formatDate(d) {
  if (!d) return "";
  const date = new Date(d);
  return date.toLocaleDateString();
}

export function formatDateTime(d) {
  if (!d) return "";
  const date = new Date(d);
  return date.toLocaleString();
}

export function timeAgo(d) {
  if (!d) return "";
  const seconds = Math.floor((Date.now() - new Date(d).getTime()) / 1000);
  const intervals = [
    { label: 'y', seconds: 31536000 },
    { label: 'mo', seconds: 2592000 },
    { label: 'd', seconds: 86400 },
    { label: 'h', seconds: 3600 },
    { label: 'm', seconds: 60 },
    { label: 's', seconds: 1 }
  ];
  for (const i of intervals) {
    const val = Math.floor(seconds / i.seconds);
    if (val > 0) return `${val}${i.label} ago`;
  }
  return 'just now';
}

export function roleHomePath(role) {
  switch ((role || '').toUpperCase()) {
    case 'CITIZEN':
      return '/citizen/dashboard';
    case 'BUSINESS_OWNER':
      return '/business/dashboard';
    case 'OFFICER':
    case 'ENGINEER':
      return '/officer/dashboard';
    case 'ADMINISTRATOR':
      return '/admin/dashboard';
    default:
      return '/';
  }
}

export function roleLabel(role) {
  if (!role) return '';
  const map = {
    CITIZEN: 'Citizen',
    BUSINESS_OWNER: 'Business Owner',
    OFFICER: 'Officer',
    ENGINEER: 'Engineer',
    ADMINISTRATOR: 'Administrator',
  };
  return map[role] || role;
}

export function statusLabel(status) {
  if (!status) return '';
  const map = {
    OPEN: 'Open',
    IN_PROGRESS: 'In progress',
    SUBMITTED: 'Submitted',
    UNDER_REVIEW: 'Under review',
    DOCUMENT_VERIFICATION: 'Document verification',
    FIELD_VERIFICATION: 'Field verification',
    CLARIFICATION_REQUIRED: 'Clarification required',
    CLARIFICATION_REQUESTED: 'Clarification requested',
    APPROVED: 'Approved',
    RESOLVED: 'Resolved',
    CLOSED: 'Closed',
    COMPLETED: 'Completed',
    CANCELLED: 'Cancelled',
    PENDING: 'Pending',
    REJECTED: 'Rejected',
  };
  return map[status] || status;
}

export function statusColor(status) {
  if (!status) return 'bg-gray-100 text-gray-800';
  switch (status) {
    case 'OPEN':
      return 'bg-yellow-100 text-yellow-800';
    case 'IN_PROGRESS':
      return 'bg-blue-100 text-blue-800';
    case 'RESOLVED':
      return 'bg-green-100 text-green-800';
    case 'CLOSED':
      return 'bg-gray-100 text-gray-800';
    case 'PENDING':
      return 'bg-orange-100 text-orange-800';
    case 'REJECTED':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

export function priorityColor(priority) {
  if (!priority) return 'bg-gray-100 text-gray-800';
  switch ((priority || '').toUpperCase()) {
    case 'HIGH':
      return 'bg-red-100 text-red-800';
    case 'MEDIUM':
      return 'bg-yellow-100 text-yellow-800';
    case 'LOW':
      return 'bg-green-100 text-green-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

export function getNextStatuses(status) {
  // Simplified transitions
  const map = {
    OPEN: ['IN_PROGRESS', 'PENDING', 'REJECTED'],
    IN_PROGRESS: ['RESOLVED', 'PENDING', 'REJECTED'],
    PENDING: ['IN_PROGRESS', 'REJECTED'],
    RESOLVED: ['CLOSED'],
  };
  return map[status] || [];
}

export { formatDate as formatDateOnly };
