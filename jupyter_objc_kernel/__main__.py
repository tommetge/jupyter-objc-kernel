from ipykernel.kernelapp import IPKernelApp
from .kernel import ObjCKernel
IPKernelApp.launch_instance(kernel_class=ObjCKernel)
