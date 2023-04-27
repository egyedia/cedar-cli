import fcntl
import os
import subprocess

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.style import Style

from org.metadatacenter.model.PlanTask import PlanTask
from org.metadatacenter.taskexecutor.TaskExecutor import TaskExecutor
from org.metadatacenter.util.Util import Util

console = Console()


class ShellTaskExecutor(TaskExecutor):

    def __init__(self):
        super().__init__()

    def execute(self, task: PlanTask, job_progress: Progress):
        super().display_header(task, job_progress, 'yellow', "Shell task executor")
        self.execute_shell_command_list(task, job_progress)

    def execute_shell_command_list(self, task: PlanTask, job_progress: Progress):
        repo = task.repo
        commands_to_execute = [cmd.format(repo.name) for cmd in task.command_list]
        cwd = Util.get_wd(repo)
        job_progress.print(Panel(
            "[green]" +
            " 📂️ Location  : " + cwd + "\n" +
            " 🏷️️  Repo type : " + repo.repo_type + "\n" +
            " 🖥️  Commands  :\n" + "\n".join(commands_to_execute),
            title="Execute shell command list",
            title_align="left"),
            style=Style(color="green"))
        for command in commands_to_execute:
            self.execute_shell_command(repo, command, cwd, job_progress)

    def execute_shell_command(self, repo, command, cwd, job_progress: Progress):
        job_progress.print(Panel(
            "[yellow]" +
            " 📂️ Location  : " + cwd + "\n" +
            " 🏷️️  Repo type : " + repo.repo_type + "\n" +
            " 🖥️  Command   : " + command,
            title="Shell subprocess",
            title_align="left"),
            style=Style(color="yellow"))
        proc = subprocess.Popen([command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=cwd)

        proc_stdout = proc.stdout
        fl = fcntl.fcntl(proc_stdout, fcntl.F_GETFL)
        fcntl.fcntl(proc_stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        stdout_parts = []
        while proc.poll() is None:
            self.handle_shell_stdout(proc_stdout, stdout_parts, job_progress)

        self.handle_shell_stdout(proc_stdout, stdout_parts, job_progress)

        msg = "[green]Processing " + repo.name + ' done. '
        if len(stdout_parts) != repo.expected_build_lines:
            msg += "[yellow]" + str(len(stdout_parts)) + ' lines vs expected ' + str(repo.expected_build_lines)
        job_progress.print(Panel(msg, style=Style(color="green"), subtitle="Shell subprocess"))
        return stdout_parts

    @staticmethod
    def handle_shell_stdout(proc_stream, my_buffer, job_progress: Progress, echo_streams=True):
        try:
            for s in iter(proc_stream.readline, b''):
                out = s.decode('utf-8').strip()
                if len(out) > 0:
                    my_buffer.append(out)
                    if echo_streams:
                        job_progress.print(out, markup=False)
                    job_progress.update(1, advance=1)
        except IOError:
            pass
