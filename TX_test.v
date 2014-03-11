`timescale 1ns / 1ps

////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer:
//
// Create Date:   16:09:35 02/24/2014
// Design Name:   async_transmitter
// Module Name:   C:/Users/workPort/Downloads/T3MAP-2013-12-01/T3MAP/ATLYS_T3_13114/TX_test.v
// Project Name:  ATLYS_T3_13114
// Target Device:  
// Tool versions:  
// Description: 
//
// Verilog Test Fixture created by ISE for module: async_transmitter
//
// Dependencies:
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
////////////////////////////////////////////////////////////////////////////////

module TX_test;

	// Inputs
	reg clk;
	reg clk2;
	reg TxD_start;
	reg [7:0] TxD_data;


	// Outputs
	//wire TxD;
	wire TxD_busy;
	wire [7:0] RxD_data;
	wire RxD_idle;
	wire RxD_endofpacket;
	wire RxD_data_ready;

	// Instantiate the Unit Under Test (UUT)
	async_transmitter uut (
		.clk(clk), 
		.TxD_start(TxD_start), 
		.TxD_data(TxD_data), 
		.TxD(TxD), 
		.TxD_busy(TxD_busy)
	);
	
	async_receiver uut2 (
		.clk(clk2),
		.RxD(TxD),
		.RxD_data_ready(RxD_data_ready),
		.RxD_endofpacket(RxD_endofpacket),
		.RxD_data(RxD_data),
		.RxD_idle(RxD_idle)
	);

	initial begin
		// Initialize Inputs
		clk = 0;
		clk2 = 0;
		TxD_start = 0;
		TxD_data = 0;

		// Wait 100 ns for global reset to finish
		#100;
		TxD_data = 8'b01010101;
		TxD_start  = 1'b1;
		#10;
		TxD_start = 1'b0;
        
		// Add stimulus here

	end
	
	always #5 clk = ~clk;
	always #5 clk2 = ~clk2;
      
endmodule

