from queue import Queue
from threading import Thread
from sys import platform as Platform

from ipykernel.kernelbase import Kernel
import re
import subprocess
import tempfile
import os
import os.path as path


class RealTimeSubprocess(subprocess.Popen):
    """
    A subprocess that allows to read its stdout and stderr in real time
    """

    def __init__(self, cmd, write_to_stdout, write_to_stderr):
        """
        :param cmd: the command to execute
        :param write_to_stdout: a callable that will be called with chunks of data from stdout
        :param write_to_stderr: a callable that will be called with chunks of data from stderr
        """
        self._write_to_stdout = write_to_stdout
        self._write_to_stderr = write_to_stderr

        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = "/home/tom/GNUstep/Library/Libraries:/usr/GNUstep/Local/Library/Libraries:/usr/GNUstep/System/Library/Libraries"
        super().__init__(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, env=env)

        self._stdout_queue = Queue()
        self._stdout_thread = Thread(target=RealTimeSubprocess._enqueue_output, args=(self.stdout, self._stdout_queue))
        self._stdout_thread.daemon = True
        self._stdout_thread.start()

        self._stderr_queue = Queue()
        self._stderr_thread = Thread(target=RealTimeSubprocess._enqueue_output, args=(self.stderr, self._stderr_queue))
        self._stderr_thread.daemon = True
        self._stderr_thread.start()

    @staticmethod
    def _enqueue_output(stream, queue):
        """
        Add chunks of data from a stream to a queue until the stream is empty.
        """
        for line in iter(lambda: stream.read(4096), b''):
            queue.put(line)
        stream.close()

    def write_contents(self):
        """
        Write the available content from stdin and stderr where specified when the instance was created
        :return:
        """

        def read_all_from_queue(queue):
            res = b''
            size = queue.qsize()
            while size != 0:
                res += queue.get_nowait()
                size -= 1
            return res

        stdout_contents = read_all_from_queue(self._stdout_queue)
        if stdout_contents:
            self._write_to_stdout(stdout_contents)
        stderr_contents = read_all_from_queue(self._stderr_queue)
        if stderr_contents:
            self._write_to_stderr(stderr_contents)


class ObjCKernel(Kernel):
    implementation = 'jupyter_objc_kernel'
    implementation_version = '0.1'
    language = 'objc'
    language_version = '2'
    language_info = {'name': 'objc',
                     'mimetype': 'text/plain',
                     'file_extension': '.m'}
    banner = "Obj-C kernel.\n" \
             "Uses clang and creates source code files and executables in temporary folder.\n"

    def __init__(self, *args, **kwargs):
        super(ObjCKernel, self).__init__(*args, **kwargs)
        self.files = []
        mastertemp = tempfile.mkstemp(suffix='.out')
        os.close(mastertemp[0])
        self.master_path = mastertemp[1]
        filepath = path.join(path.dirname(path.realpath(__file__)), 'resources', 'master.c')
        subprocess.call(['clang', filepath, '-std=c11', '-rdynamic', '-ldl', '-o', self.master_path])
        self.objc_flags = []
        self.objc_libs = ['-framework', 'Foundation']
        if Platform == 'linux':
            self.objc_flags = subprocess.check_output(['/usr/GNUstep/System/Tools/gnustep-config', '--objc-flags']).split()
            self.objc_libs = subprocess.check_output(['/usr/GNUstep/System/Tools/gnustep-config', '--objc-libs']).split()
            self.objc_libs.append('-lgnustep-base')

    def cleanup_files(self):
        """Remove all the temporary files created by the kernel"""
        for file in self.files:
            os.remove(file)
        os.remove(self.master_path)

    def new_temp_file(self, **kwargs):
        """Create a new temp file to be deleted when the kernel shuts down"""
        # We don't want the file to be deleted when closed, but only when the kernel stops
        kwargs['delete'] = False
        kwargs['mode'] = 'w'
        file = tempfile.NamedTemporaryFile(**kwargs)
        self.files.append(file.name)
        return file

    def _write_to_stdout(self, contents):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': contents})

    def _write_to_stderr(self, contents):
        self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': contents})

    def _convert(self, s):
        try:
            return str(s,encoding='utf8')
        except:
            return s

    def create_jupyter_subprocess(self, cmd):
        return RealTimeSubprocess(cmd,
                                  lambda contents: self._write_to_stdout(contents.decode()),
                                  lambda contents: self._write_to_stderr(contents.decode()))

    def compile_with_clang(self, source_filename, binary_filename, cflags=None, ldflags=None):
        cflags = self.objc_flags + cflags
        ldflags = self.objc_libs + ldflags + ['-shared', '-rdynamic']
        args = ['clang'] + cflags + ldflags + [source_filename, '-o', binary_filename]
        # self._write_to_stderr(" ".join(map(lambda x: self._convert(x), args)) + "\n")
        return self.create_jupyter_subprocess(args)

    def _filter_magics(self, code):

        magics = {'cflags': [],
                  'ldflags': [],
                  'args': []}

        for line in code.splitlines():
            if line.startswith('//%'):
                key, value = line[3:].split(":", 2)
                key = key.strip().lower()

                if key in ['ldflags', 'cflags']:
                    for flag in value.split():
                        magics[key] += [flag]
                elif key == "args":
                    # Split arguments respecting quotes
                    for argument in re.findall(r'(?:[^\s,"]|"(?:\\.|[^"])*")+', value):
                        magics['args'] += [argument.strip('"')]

        return magics

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):

        magics = self._filter_magics(code)

        with self.new_temp_file(suffix='.m') as source_file:
            source_file.write(code)
            source_file.flush()
            with self.new_temp_file(suffix='.out') as binary_file:
                p = self.compile_with_clang(source_file.name, binary_file.name, magics['cflags'], magics['ldflags'])
                while p.poll() is None:
                    p.write_contents()
                p.write_contents()
                if p.returncode != 0:  # Compilation failed
                    self._write_to_stderr(
                            "[Obj-C kernel] clang exited with code {}, the executable will not be executed".format(
                                    p.returncode))
                    return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [],
                            'user_expressions': {}}

        p = self.create_jupyter_subprocess([self.master_path, binary_file.name] + magics['args'])
        while p.poll() is None:
            p.write_contents()
        p.write_contents()

        if p.returncode != 0:
            self._write_to_stderr("[Obj-C kernel] Executable exited with code {}".format(p.returncode))
        return {'status': 'ok', 'execution_count': self.execution_count, 'payload': [], 'user_expressions': {}}

    def do_shutdown(self, restart):
        """Cleanup the created source code files and executables when shutting down the kernel"""
        self.cleanup_files()
