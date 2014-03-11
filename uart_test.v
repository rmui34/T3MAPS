`timescale 1ns / 1ps

////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer:
//
// Create Date:   01:24:41 01/29/2014
// Design Name:   top
// Module Name:   C:/Users/workPort/Downloads/T3MAP-2013-12-01/T3MAP/TMAPS_UART_TEST/uart_test.v
// Project Name:  TMAPS_UART_TEST
// Target Device:  
// Tool versions:  
// Description: 
//
// Verilog Test Fixture created by ISE for module: top
//
// Dependencies:
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
////////////////////////////////////////////////////////////////////////////////

module uart_test;

	parameter bit_time = 104000; // nanoseconds

	// Inputs
	reg uartRx_pin;
	reg CLK;
	reg Reset;
	wire data_in;

	// Outputs
	wire [7:0] cmd;
	wire [7:0] LED;
	wire uartTx_pin;
	wire clk_out;

	// Instantiate the Unit Under Test (UUT)
	top uut (
		.cmd(cmd), 
		.LED(LED), 
		.uartTx_pin(uartTx_pin), 
		.clk_out(clk_out), 
		.uartRx_pin(uartRx_pin), 
		.CLK(CLK), 
		.Reset(Reset),
		.data_in(data_in)
	);

	assign data_in = cmd[6];

	initial begin
		// Initialize Inputs
		uartRx_pin = 1;
		CLK = 0;
		Reset = 1;
		#100;
		Reset = 0;
		#100;
		Reset = 1;
//*******ALL VALUES LSB!!!!!!!!!!!!!!!!!!!!!!
//^not really just rember 8 is not the last byte you read, it's the first byte...
		// WEnable fifo for data 
		#bit_time;
		uartRx_pin = 0; //Start 
      #bit_time;
		uartRx_pin = 1; //1
      #bit_time;
		uartRx_pin = 1; //2
      #bit_time;
		uartRx_pin = 1; //3
      #bit_time;
		uartRx_pin = 1; //4
      #bit_time;
		uartRx_pin = 1; //5
      #bit_time;
		uartRx_pin = 1; //6
      #bit_time;
		uartRx_pin = 1; //7
      #bit_time; 
		uartRx_pin = 1; //8
      #bit_time;
		uartRx_pin = 1; //STOP
		////////////////////// Data byte
      #bit_time;
		uartRx_pin = 0; //Start
      #bit_time;
		uartRx_pin = 1; //1
      #bit_time;
		uartRx_pin = 0; //2
      #bit_time;
		uartRx_pin = 1; //3
      #bit_time;
		uartRx_pin = 0; //4
      #bit_time;
		uartRx_pin = 1; //5
      #bit_time;
		uartRx_pin = 0; //6
      #bit_time;
		uartRx_pin = 1; //7
      #bit_time; 
		uartRx_pin = 0; //8
      #bit_time;
		uartRx_pin = 1; //STOP
      #bit_time;
		////////////////////// Data byte 2
      #bit_time;
		uartRx_pin = 0; //Start
      #bit_time;
		uartRx_pin = 1; //1
      #bit_time;
		uartRx_pin = 0; //2
      #bit_time;
		uartRx_pin = 0; //3
      #bit_time;
		uartRx_pin = 0; //4
      #bit_time;
		uartRx_pin = 0; //5
      #bit_time;
		uartRx_pin = 0; //6
      #bit_time;
		uartRx_pin = 0; //7
      #bit_time; 
		uartRx_pin = 0; //8
      #bit_time;
		uartRx_pin = 1; //STOP
      #bit_time;
		////////////////////// Data byte 3
      #bit_time;
		uartRx_pin = 0; //Start
      #bit_time;
		uartRx_pin = 1; //1
      #bit_time;
		uartRx_pin = 0; //2
      #bit_time;
		uartRx_pin = 0; //3
      #bit_time;
		uartRx_pin = 0; //4
      #bit_time;
		uartRx_pin = 1; //5
      #bit_time;
		uartRx_pin = 1; //6
      #bit_time;
		uartRx_pin = 0; //7
      #bit_time; 
		uartRx_pin = 1; //8
      #bit_time;
		uartRx_pin = 1; //STOP
      #bit_time;
		/////////////////////// Stop getting data (will this load into fifo????)
		#bit_time;
		uartRx_pin = 0; //Start
      #bit_time;
		uartRx_pin = 0; //1
      #bit_time;
		uartRx_pin = 1; //2
      #bit_time;
		uartRx_pin = 1; //3
      #bit_time;
		uartRx_pin = 1; //4
      #bit_time;
		uartRx_pin = 1; //5
      #bit_time;
		uartRx_pin = 1; //6
      #bit_time;
		uartRx_pin = 1; //7
      #bit_time; 
		uartRx_pin = 1; //8
      #bit_time;
		uartRx_pin = 1; //STOP
      #bit_time;
		////////////////////// Enable Write
		#bit_time;
		uartRx_pin = 0; //Start
      #bit_time;
		uartRx_pin = 1; //1
      #bit_time;
		uartRx_pin = 1; //2
      #bit_time;
		uartRx_pin = 1; //3
      #bit_time;
		uartRx_pin = 1; //4
      #bit_time;
		uartRx_pin = 1; //5
      #bit_time;
		uartRx_pin = 1; //6
      #bit_time;
		uartRx_pin = 1; //7
      #bit_time; 
		uartRx_pin = 0; //8
      #bit_time;
		uartRx_pin = 1; //STOP
      #bit_time;
		#bit_time;
		#bit_time;
		////////////////////// Enable Tx (Just to check)
		#bit_time;
		uartRx_pin = 0; //Start
      #bit_time;
		uartRx_pin = 0; //1
      #bit_time;
		uartRx_pin = 1; //2
      #bit_time;
		uartRx_pin = 1; //3
      #bit_time;
		uartRx_pin = 1; //4
      #bit_time;
		uartRx_pin = 1; //5
      #bit_time;
		uartRx_pin = 1; //6
      #bit_time;
		uartRx_pin = 1; //7
      #bit_time; 
		uartRx_pin = 0; //8
      #bit_time;
		uartRx_pin = 1; //STOP
      #bit_time;
		
		#bit_time;
		// Add stimulus here

	end
	
	always #5 CLK = ~CLK; //100Mhz clock
      
endmodule

