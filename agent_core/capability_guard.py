def check_capability(step):

    tool = step.tool
    args = step.args
    capability = step.capability

    if tool == "GIT_RUN":

        sub = args.get("subcommand")

        read_ops = {"status", "diff", "log"}
        write_ops = {"init", "add", "commit"}

        if sub in read_ops and capability != "repo_read":
            raise PermissionError("GIT read requires repo_read")

        if sub in write_ops and capability != "repo_write":
            raise PermissionError("GIT write requires repo_write")
