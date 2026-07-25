export class ValidationError extends Error {
	public constructor(message: string) {
		super(message);
		this.name = "ValidationError";
	}
}

export class NotFoundError extends Error {
	public constructor(message: string) {
		super(message);
		this.name = "NotFoundError";
	}
}

export class UpstreamServiceError extends Error {
	public constructor(message: string) {
		super(message);
		this.name = "UpstreamServiceError";
	}
}

export class NotImplementedError extends Error {
	public constructor(message: string) {
		super(message);
		this.name = "NotImplementedError";
	}
}
