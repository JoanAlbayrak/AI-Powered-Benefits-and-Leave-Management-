/** One in-flight action; an ambiguous result requires a successful scoped read. */
export class WorkflowController {
  pending = false;
  uncertainContext = null;

  get blocked() { return this.pending || this.uncertainContext !== null; }

  async execute(context, action) {
    if (this.blocked) return { accepted: false };
    this.pending = true;
    try {
      return { accepted: true, result: await action() };
    } catch (error) {
      if (error.outcomeUnknown) this.uncertainContext = context;
      return { accepted: true, error };
    } finally {
      this.pending = false;
    }
  }

  reconcile(context) {
    if (!this.pending && context === this.uncertainContext) this.uncertainContext = null;
  }
}
