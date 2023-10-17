import os
import subprocess
import sys


class PyKotaAccounterError(Exception):
    """An exception for Accounter related stuff."""

    def __init__(self, message=""):
        self.message = message
        Exception.__init__(self, message)

    def __repr__(self):
        return self.message

    __str__ = __repr__


class ContarSubprocess:

    def __init__(self, filename):
        self.arguments = '/usr/local/bin/pkpgcounter'
        self.MEGABYTE = 1024 * 1024
        self.infile = open(filename, "rb")
        self.filename = filename

    def run(self):
        child = subprocess.Popen([self.arguments, self.filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE)

        try:
            data = self.infile.read(self.MEGABYTE)
            while data:
                print(f"teste {data.__sizeof__()}")

                #child.stdin.read(data)
                data = self.infile.read(self.MEGABYTE)
        except (IOError, OSError) as msg:
            msg = f"{self.arguments} : {msg}"
            print(f"Unable to compute job size with accounter {msg}")

        self.infile.close()
        pagecounter = None

        try:
            answer, stderr = child.communicate()
            sys.stdout.write(answer.decode())
            print(child.returncode)
        except (IOError, OSError) as msg:
            msg = f"{self.arguments} : {msg}"
            print(f"Unable to compute job size with accounter {msg}")
        else:
            lines = [l.strip() for l in answer.split(b'\n')]
            for i in range(len(lines)):
                try:
                    pagecounter = int(lines[i])
                except (AttributeError, ValueError):
                    print(f"Line [{lines[i]}] skipped in accounter's output. Trying again...")
                else:
                    break
        child.kill()

        try:
            status = child.wait()
        except OSError as msg:
            print(f"Problem while waiting for software accounter pid {child.pid} to exit : {msg}")
        else:
            if os.WIFEXITED(status):
                status = os.WEXITSTATUS(status)
            print(f"Software accounter {self.arguments} exit code is {str(status)}")


        print(f"Software accounter {self.arguments} said job is {repr(pagecounter)} pages long.")


        return pagecounter


if __name__ == "__main__":
    p = ContarSubprocess('/home/ubuntu/xps52.oxps')
    print(p.run())
