   case SLC_CSK:
      INFO.reset();// make sure nothing in buffer
      INFO << "csk_dump_header2doris.py "
     << input_m_readfiles.datfile  // this should be HD5 file for Cosmo-skymed
     << " > scratchres_csk" << endl << ends;
      //char cmd[512];// command string
      strcpy(cmd, INFO.get_str());
      INFO.print("With following command the Cosmo-skymed header was read.");
      INFO.print(cmd);
      PROGRESS.print("Making system call to csk_dump_header2doris.py");
      PROGRESS.print("(also requires python, numpy and hd5 libraries)");
      status=system(cmd);// this does the work   
      if (status != 0)                                                          // [MA] TODO make it a function
        {
        ERROR << "csk_dump_header2doris.py: failed with exit code: " << status;
        PRINT_ERROR(ERROR.get_str())
        throw(some_error);
        }
      INFO.reset();
      PROGRESS.print("Finished system call to csk_dump_header2doris.py");
      // ___ update resfile ___
      updatefile("scratchres_csk",input_general.m_resfile);
      // ___ update logfile ___
      // updatefile("csk_dump_header.log",input_general.logfile);
      break;