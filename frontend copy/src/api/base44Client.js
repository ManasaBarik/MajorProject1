// base44Client placeholder — provide a minimal named `base44` export
// so the app can run in dev without a configured Base44 backend.
export const base44 = {
	auth: {
		// return null by default (no user)
		me: async () => null,
		// no-op logout (accept optional redirect)
		logout: (redirectUrl) => {
			try {
				// if a redirectUrl is provided, navigate there
				if (redirectUrl) window.location.href = redirectUrl;
			} catch (e) {
				// ignore in non-browser environments
			}
		},
		// redirectToLogin stub
		redirectToLogin: (redirectUrl) => {
			try {
				if (redirectUrl) window.location.href = redirectUrl;
			} catch (e) {}
		},
	},
};

export default base44;
