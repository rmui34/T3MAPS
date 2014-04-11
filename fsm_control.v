`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date:    16:05:46 01/13/2014 
// Design Name: 
// Module Name:    fsm_control 
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
 module fsm_control(
    input clk_100,
    input Reset,
    input [7:0] rx_byte,
	 input PROBLEM,
	 input fifoEmpty1,
	 input fifoEmpty2,
	 input rx_ready,
	 input tx_busy,
	 input wr_ack,
	 input rd_ack,
	 input SW0,
	 output [7:0] LED,
    output wr_en1,
    output wr_en2,
    output rd_en1,
    output rd_en2,
	 output tx_en
    );
	 
//registers below used in FSM and other sequential logic 
reg reg_wr_en1;
reg reg_wr_en2;
reg reg_rd_en1;
reg reg_rd_en2;
reg reg_en_tx;
reg [7:0] reg_LED;
initial reg_LED = 8'b00000000;
//assign registers above to their respective wires. 
assign wr_en1 = reg_wr_en1;
assign wr_en2 = reg_wr_en2;
assign rd_en1 = reg_rd_en1;
assign rd_en2 = reg_rd_en2;
assign tx_en = reg_en_tx;
assign LED[7:0] = reg_LED;

//4 States for FSM. Using one hot encoding, although implenation converts this to gray encoding. 
parameter SIZE = 4; 
parameter IDLE  = 4'b0001; 
parameter DATA = 4'b0010;
parameter WRITE = 4'b0100;
parameter TRANSMIT = 4'b1000;
reg [SIZE-1:0] state; //state register
initial state = IDLE;
initial reg_wr_en1 <= 1'b0;
initial reg_wr_en2 <= 1'b0;
initial reg_rd_en1 <= 1'b0;
initial reg_rd_en2 <= 1'b0;
initial reg_en_tx <= 1'b0;

//always statement for FSM and LED logic
always @ (posedge clk_100) begin
//Finite state machine
begin: FSM
	//reset the registers to known values upon a reset.
	if (Reset) begin //Active high reset
		state <= IDLE; //set FSM state to idle
		reg_LED[7:0] <= 8'b00000000; //clear LEDs
		reg_wr_en1 <= 1'b0;
		reg_wr_en2 <= 1'b0;
		reg_rd_en1 <= 1'b0;
		reg_rd_en2 <= 1'b0;
		reg_en_tx <= 1'b0;
	end else
		case(state)
			IDLE: 
				if (rx_byte == 8'b11111111 && rx_ready) begin  //if uart receives all ones, enter the data state.
					state <= DATA;
				end else if (rx_byte == 8'b01111111 && rx_ready) begin //enter the write state.
					state <= WRITE;
				end else if (rx_byte == 8'b01111110 && rx_ready) begin //enter the transmit state.
					state <= TRANSMIT;
				end else begin
					state <= IDLE; //remain in idle state if rxData is not one of the above values.
					reg_wr_en1 <= 1'b0; //Next five lines reset all fifo/uart control registers to
					reg_wr_en2 <= 1'b0; //0 since each state enables what it needs. 
					reg_rd_en1 <= 1'b0;
					reg_rd_en2 <= 1'b0;
					reg_en_tx <= 1'b0;	
					reg_LED[0] <= 1'b1; //Set the idle LED true
					reg_LED[4] <= 1'b0;
					reg_LED[2:1] <= 3'b00; //Clear the other LEDs
				end	
			DATA: if (rx_byte == 8'b11111110 & rx_ready & SW0) begin //signal to stop receiving data into fifo1
						state <= IDLE;
						reg_LED[7] <= 0;
					end else if (rx_byte == 8'b11111110 & rx_ready & !SW0) begin //Long way to do this...
						state <= WRITE;
						reg_LED[7] <= 0;
						reg_wr_en1 <= 1'b0; //Next five lines reset all fifo/uart control registers to
						reg_wr_en2 <= 1'b0; //0 since each state enables what it needs. 
						reg_rd_en1 <= 1'b0;
						reg_rd_en2 <= 1'b0;
						reg_en_tx <= 1'b0;	
						reg_LED[0] <= 1'b1; //Set the idle LED true
						reg_LED[4] <= 1'b0;
						reg_LED[2:1] <= 3'b00; //Clear the other LEDs
					end else begin
						if (rx_ready & rx_byte != 8'b11111111) begin
							reg_LED[7] <= 1'b0;
							reg_wr_en1 <= 1; //enable fifo1 write
							reg_LED[6] <= 1'b0; //Turn off transmit light
						end
						if(wr_ack) begin //make sure double write does not occur
							reg_wr_en1 <= 0; 
							reg_LED[6] <= 1'b1; //make it blink a lot
						end
						reg_LED[7] <= 1'b1; //(Why is this here???)
						reg_LED[1] <= 1'b1; //enable LED1 to indicate state. 
						state <= DATA; //remain in data state.
				end
			//review this maybe
			WRITE:if (fifoEmpty1 & SW0) begin //If fifo1 is empty, then either a write error occured or we are done
					reg_LED[3] <= 1'b1;    //signal write state finishing.
					state <= IDLE;			  //go back to idle state. 	
				end else if (fifoEmpty1 & !SW0) begin 
					reg_LED[3] <= 1'b1;
					state <= TRANSMIT;
					reg_wr_en1 <= 1'b0; //Next five lines reset all fifo/uart control registers to
					reg_wr_en2 <= 1'b0; //0 since each state enables what it needs. 
					reg_rd_en1 <= 1'b0;
					reg_rd_en2 <= 1'b0;
					reg_en_tx <= 1'b0;	
					reg_LED[0] <= 1'b1; //Set the idle LED true
					reg_LED[4] <= 1'b0;
					reg_LED[2:1] <= 3'b00;
				end else begin
					reg_LED[3] <= 1'b0;	  //have finished outputting all of the data in fifo1.
					reg_rd_en1 <= 1'b1;     //enable fifo1 read. 
					reg_wr_en2 <= 1'b1;	  //start collecting data from datain pin using fifo2.
					reg_LED[2] <= 1'b1;	  //Turn on the 3rd LED to signal state.
					state <= WRITE;        //remain in write state.
				end
			//transmit data stored in fifo2 to uart
			TRANSMIT: if (fifoEmpty2 && ~tx_busy & SW0) begin //stop transmitting. This may need to be modifed.
					state <= IDLE; //Go back to idle state. Should rewrite to avoid sending a signal...
					reg_LED[6] <= 1'b1; //Signal Transmit finished. 
					end else begin
						reg_LED[6] <= 1'b0;
						reg_LED[0] <= 1'b0;
						if(~tx_busy) begin
							reg_rd_en2 <= 1'b1;
						end else begin
							reg_rd_en2 <= 1'b0;
						end
						
						if(rd_ack) begin
							reg_en_tx <= 1'b1;
							reg_LED[4] <= 1'b1;
							reg_rd_en2 <= 1'b0;
						end else begin
							reg_en_tx <= 1'b0;
							reg_LED[4] <= 1'b0;
						end
						state <= TRANSMIT;  //keep transmitting. 
					end		
			default: state <= IDLE; //This is the default state, waiting for data
		endcase
		
		if (Reset == 1'b1) begin
			reg_LED[5] <= 1'b0; //clear LED #5
		end
		else if (PROBLEM) begin
			reg_LED[5] <= 1'b1; //if fifos have an issue, such as either are full or both are empty.
		end
		else begin
			reg_LED[5] <= 1'b0; //otherwise everything is fine. 
		end
	end
end

endmodule
