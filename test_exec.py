import traceback

class TestExec:
    """This class enables simplyfied testing
    Initialize with a method or lambda to be called
    Execute test calling execute() method
    Test methods shall take as first parameter the instance of TestExec.
    Through the TestExec instance these methods may be called:
        report(): To report a result
        call_except(): To call a method expecting an Exception. 
                       Make use of lambda methods as required.
    """
    def __init__(self, method):
        self.method = method
        self.name = method.__qualname__
        self.success = True
        
    def __del__(self):
        print("Test {} {}".format(self.name, "successfully passed" if self.success else "failed!"))
    
    def execute(self, *args, **kwargs):
        self.call_except(lambda: self.method(self, *args, **kwargs))
                
    def call_except(self, method, expected_exception=None, verbose=False):
        if expected_exception:
            try:
                method()
            except expected_exception:
                if (verbose):
                    self.report(True, "Exception rised as expected")
            except BaseException as e:
                self.report(False, "Unexpected execption caught", e)
            except:
                self.report(False, "Unknown exception caught")
            else: 
                self.report(False, "Expected exception {} was not raised".format(expected_exception))
        else:
            try:
                method()
            except BaseException as e:
                self.report(False, "Unexpected execption caught", e)
            except:
                self.report(False, "Unknown exception caught")
                 
    def report(self, success, text, error=None):
        if success: 
            print("Success: ", end = "")
        else:
            self.success = False
            print("Failed: ", end = "")
        print(self.name + ": ", end = "")
        if error:
            print(text, ": ", type(error))
            print(traceback.format_exc())
        else:
            print(text)
