export function Greeting() {
  return (
    <div className="rounded-2xl border bg-card p-6 text-sm text-muted-foreground shadow-sm">
      <h2 className="text-base font-semibold text-foreground">
        Welcome to the Rev LangGraph demo
      </h2>
      <p className="mt-2">
        Ask about the deposition, request a summary, or upload a document to
        ground the response.
      </p>
    </div>
  );
}
