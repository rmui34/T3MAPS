`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company:  Universitiy of Washington
// Engineer: Maximilian Golub
// 
// Create Date:    15:42:28 12/28/2013 
// Design Name: 
// Module Name:    uartControl 
// Project Name: 
// Target Devices: 
// Tool versions: 
// Description: 
//
// Dependencies: 
//
// Revision: 
// Revision 0.01 - File Created
// Additional Comments: 
//
//////////////////////////////////////////////////////////////////////////////////
module uartControl(
	input 	clk_100,
	input		clk_25,
	input		clk_5,
	input 	Reset,
	input 	lock,
	input	 	rx,
	input 	data,
	output 	tx,
	output 	[7:0] cmd,
	output 	[7:0] LED,
	output   [10:0] wr_data_count, // output [10 : 0] wr_data_count
	output 	[1:0] rx_extra
   );

wire [7:0] tx_byte; //Used to prevent sythesis from assuming a 1 bit wire
wire [7:0] rx_byte; //Used to prevent sythesis from assuming a 1 bit wire
wire rst; //True reset for modules
assign rst = Reset || ~lock;	

async_transmitter tx_mod(
	.clk			(clk_100),
	.TxD_start	(tx_en),
	.TxD_data	(tx_byte),
	.TxD			(tx),
	.TxD_busy	(tx_busy)
);

async_receiver rx_mod(
	.clk				(clk_100),
	.RxD				(rx),
	.RxD_data_ready(rx_ready),
	.RxD_data		(rx_byte[7:0]),  // data received, valid only (for one clock cycle) when RxD_data_ready is asserted

	// We also detect if a gap occurs in the received stream of characters
	// That can be useful if multiple characters are sent in burst
	//  so that multiple characters can be treated as a "packet"
	.RxD_idle		 (rx_extra[0]),  // asserted when no data has been received for a while
	.RxD_endofpacket(rx_extra[1]) // asserted for one clock cycle when a packet has been detected (i.e. RxD_idle is going high)
);

//Wrapper for the two fifos used in this design. 
fifos memory(
	.clk_25				(clk_25), //fifo1 write clock and fifo2 read clock.
	.clk_5				(clk_5),  //fifo1 read clock and fifo2 write clock. 
	.rst					(rst),  //reset the fifos. Active low reset. 
	.wr_en1				(wr_en1), //enable write to fifo1.
	.wr_en2				(wr_en2), //enable write to fifo2
	.rd_en1				(rd_en1), //enable read to fifo1.
	.rd_en2				(rd_en2), //enable read tot fifo2.
	.datain				(data),   //single bit data from input pin. Stored to fifo2. 
	.rxData				(rx_byte[7:0]), //8 bit data from uart. Stored to fifo1.
	.wr_ack				(wr_ack),
	.rd_ack				(rd_ack),
	.problem				(PROBLEM),//signal true if either fifo1 or fifo2 is full, or if both are empty.
	.txData				(tx_byte[7:0]), //8 bit data from fifo2 to uart.
	.cmd					(cmd[7:0]),	 //8 bit data from fifo1 to cmd pins. 
	.empty1			   (fifoEmpty1), //signal from fifo1 if it is empty. 	
	.empty2				(fifoEmpty2),
	.wr_data_count		(wr_data_count[10:0]) // output [10 : 0] wr_data_count
	);

//Finite state machine
//Centeral control of the system
//Centers around rx commands decoded by the uart module.
fsm_control fsm1(
	.clk_100		(clk_100),
	.Reset		(rst),
	.LED			(LED[7:0]),
	.rx_byte		(rx_byte[7:0]),
	.rx_ready	(rx_ready),
	.wr_ack		(wr_ack),
	.rd_ack		(rd_ack),
	.wr_en1		(wr_en1),
	.wr_en2		(wr_en2),
	.rd_en1		(rd_en1),
	.rd_en2		(rd_en2),
	.tx_en		(tx_en),
	.tx_busy		(tx_busy),
	.fifoEmpty1 (fifoEmpty1),
	.fifoEmpty2 (fifoEmpty2),
	.tx_sig_byte(tx_sig_byte),
	.PROBLEM		(PROBLEM)
	);

endmodule
