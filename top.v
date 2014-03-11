`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: Univeristy of Washington
// Engineer: 
// 
// Create Date:    13:09:04 12/28/2013 
// Design Name:    T3MAPS DAQ
// Module Name:    top 
// Project Name: 
// Target Devices: ATLYS Spartan 6
// Tool versions: ISE 14.7
// Description: 
//
// Dependencies: 
//
// Revision: 
// Revision 0.01 - File Created
// Additional Comments: 
//

//Add a count to the fifo
//////////////////////////////////////////////////////////////////////////////////
module top(
    output [7:0] cmd, //8 bit command bitstream.
	 output [7:0] LED, //Status LEDS.	
	 output uartTx_pin,//Connects to Exar usb-uart bridge.
	 output clk_out, //5 Mhz clock out. 
	 output rx_idle,
	 output rx_packet,
	 output [10:0] wr_data_count, // output [10 : 0] wr_data_count (keeps optimizer happy)
	 input uartRx_pin, //Connects to the Exar usb-uart bridge.
    input data_in, //data input from prototype sensor chip
    input CLK, //100Mhz clock from crystal
    input Reset //Reset button on the ATLYS demo board. (Debounce?)
    );
	 
wire [1:0] rx_extra;
//wire [10:0] wr_data_count;
assign rx_idle = rx_extra[0];
assign rx_packet = rx_extra[1]; 

//The module in charge of controlling the uart and fifos. The three clocks are 
//driven by the PLL built into the Spartan 6 chip. Reset comes from the external
//Reset button, and rx and tx connect to external pins as well. 
uartControl control(
	.clk_100	(clk_100),
	.clk_25	(clk_25),
	.clk_5	(clk_5),
	.Reset	(~Reset),
	.lock		(lock),
	.rx		(uartRx_pin),
	.tx		(uartTx_pin),
	.data		(data_in),
	.cmd		(cmd[7:0]),
	.LED		(LED[7:0]),
	.wr_data_count(wr_data_count[10:0]), // output [10 : 0] wr_data_count
	.rx_extra(rx_extra[1:0]) //keeps optimizer happy...not used
	);

//This was created by Xilinx coregen. 
clkout clkgen
   (// Clock in ports
    .clk				(CLK),      // IN - This is 100 MHz
										// Clock out ports
    .clk_100		(clk_100),  // OUT - 100 MHz
    .clk_25			(clk_25),   // OUT - 25 MHz for uart and fifo1 write 	and fifo2 read.
    .clk_5			(clk_5),    // OUT - % MHz for fifo1 read out and fifo2 write.
    .clk_5_out		(clk_5_out),// OUT - % Mhz out to ODDR2 inst.
	 //.uart_clk		(),
    // Status and control signals
	 .lock			(lock),
    .Reset			(~Reset));   // IN - Reset Active low on ATLYS
	 
wire not_clk_5_out;
assign not_clk_5_out = ~clk_5_out; //setup for ODDR2



//Because map proccess suggests doing this. 
ODDR2 #(
      .DDR_ALIGNMENT("NONE"),
      .INIT(1'b0),
      .SRTYPE("SYNC"))
ODDR2_ins (
	.Q 	(clk_out), //Output to pin
	.C0	(clk_5_out), //Normal input
	.C1	(not_clk_5_out), //Inverted input
	.CE	(1'b1), //Tied to logic 1
	.D0	(1'b1), //Tied to logic 1
	.D1	(1'b0), //Tied to logic 0
	.R		(1'b0), //Reset locked to 0
	.S		(1'b0));


endmodule
