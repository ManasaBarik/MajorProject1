export const workflows = {
  complaints: {
    title: "Civic Complaints",
    status: "available",
  },
  services: {
    title: "Municipal & Business Services",
    status: "available",
  },
};

export function isWorkflowAvailable(key) {
  return workflows[key]?.status === "available";
}