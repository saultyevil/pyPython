#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Description of file."""

from subprocess import PIPE, Popen


def clear_jobs():
    """Clear all the jobs from the slurm queue."""

    sh = "squeue -u $USER -o '%A'"
    stdout, stderr = Popen(sh, stdout=PIPE, stderr=PIPE, shell=True).communicate()
    job_ids = stdout.decode("utf-8").split()[1:]

    for job in job_ids:
        sh = "scancel " + job
        stdout, stderr = Popen(sh, stdout=PIPE, stderr=PIPE, shell=True).communicate()
        if stderr:
            print(stderr.decode("utf-8"))

    print(f"Removed jobs {', '.join(job_ids[:-1])} and {job_ids[-1]}.")

    return job_ids


if __name__ == "__main__":
    clear_jobs()
