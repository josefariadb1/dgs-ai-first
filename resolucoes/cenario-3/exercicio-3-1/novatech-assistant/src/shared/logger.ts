type LogPayload = Record<string, unknown>;
type LogMethod = (payload: LogPayload, message: string) => void;

const noopLog: LogMethod = () => {
	// Intentionally no-op for local starter repo.
};

export const logger: {
	info: LogMethod;
	warn: LogMethod;
	error: LogMethod;
} = {
	info: noopLog,
	warn: noopLog,
	error: noopLog,
};
