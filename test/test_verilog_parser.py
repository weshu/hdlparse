import unittest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hdlparse.verilog_parser import (
    parse_verilog,
    VerilogModule,
    VerilogParameter,
    VerilogPort,
    VerilogSubModule
)

class TestVerilogParser(unittest.TestCase):
    def test_basic_module(self):
        """Test parsing a basic module without ports"""
        verilog = """
        module basic_module();
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0].name, "basic_module")
        self.assertEqual(len(modules[0].ports), 0)

    def test_module_with_ports(self):
        """Test parsing a module with input and output ports"""
        verilog = """
        module port_module(
            input clk,
            output reg [7:0] data
        );
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 1)
        module = modules[0]
        self.assertEqual(module.name, "port_module")
        self.assertEqual(len(module.ports), 2)
        
        # Check input port
        clk_port = next(p for p in module.ports if p.name == "clk")
        self.assertIsInstance(clk_port, VerilogPort)
        self.assertEqual(clk_port.mode, "input")
        self.assertEqual(clk_port.data_type, "wire")
        
        # Check output port
        data_port = next(p for p in module.ports if p.name == "data")
        self.assertIsInstance(data_port, VerilogPort)
        self.assertEqual(data_port.mode, "output")
        self.assertEqual(data_port.data_type, "reg [7:0]")

    def test_module_with_parameters(self):
        """Test parsing a module with parameters"""
        verilog = """
        module param_module #(
            parameter WIDTH = 8,
            parameter [7:0] ADDR = 8'hFF
        )(
            input clk
        );
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 1)
        module = modules[0]
        
        # Check parameters
        width_param = next(p for p in module.generics if p.name == "WIDTH")
        self.assertIsInstance(width_param, VerilogParameter)
        self.assertEqual(width_param.data_type, "wire")
        self.assertEqual(width_param.default_value, "8")
        
        addr_param = next(p for p in module.generics if p.name == "ADDR")
        self.assertIsInstance(addr_param, VerilogParameter)
        self.assertEqual(addr_param.data_type, "wire [7:0]")
        self.assertEqual(addr_param.default_value, "8'hFF")

    def test_module_with_submodules(self):
        """Test parsing a module with submodule instances"""
        verilog = """
        module top_module(
            input clk,
            input rst
        );
            sub_module instance1 (
                .clk(clk),
                .rst(rst)
            );
            
            sub_module instance2 (
                .clk(clk),
                .rst(rst)
            );
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 1)
        module = modules[0]
        self.assertEqual(len(module.submodules), 2)
        
        # Check first submodule
        sub1 = module.submodules[0]
        self.assertEqual(sub1.module_type, "sub_module")
        self.assertEqual(sub1.instance_name, "instance1")
        
        # Check second submodule
        sub2 = module.submodules[1]
        self.assertEqual(sub2.module_type, "sub_module")
        self.assertEqual(sub2.instance_name, "instance2")

    def test_module_with_comments(self):
        """Test parsing a module with comments and metacomments"""
        verilog = """
        // This is a test module
        module comment_module(
            input clk,  // Clock input
            output reg data  // Data output
        );
            // Internal comment
            /* Block comment
               spanning multiple lines */
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 1)
        module = modules[0]
        self.assertEqual(module.name, "comment_module")
        self.assertEqual(len(module.ports), 2)

    def test_multiple_modules(self):
        """Test parsing multiple modules in the same file"""
        verilog = """
        module module1(
            input clk
        );
        endmodule

        module module2(
            input rst
        );
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 2)
        self.assertEqual(modules[0].name, "module1")
        self.assertEqual(modules[1].name, "module2")

    def test_complex_module(self):
        """Test parsing a complex module with all features"""
        verilog = """
        // Complex module test
        module complex_module #(
            parameter WIDTH = 8,
            parameter [7:0] ADDR = 8'hFF
        )(
            input clk,
            input rst_n,
            output reg [WIDTH-1:0] data,
            inout wire sda
        );
            // Submodule instances
            sub_module sub1 (
                .clk(clk),
                .rst(rst_n),
                .data(data)
            );
            
            sub_module sub2 (
                .clk(clk),
                .rst(rst_n),
                .data(data[7:0])
            );
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 1)
        module = modules[0]
        
        # Check parameters
        width_param = next(p for p in module.generics if p.name == "WIDTH")
        self.assertIsInstance(width_param, VerilogParameter)
        self.assertEqual(width_param.data_type, "wire")
        self.assertEqual(width_param.default_value, "8")
        
        addr_param = next(p for p in module.generics if p.name == "ADDR")
        self.assertIsInstance(addr_param, VerilogParameter)
        self.assertEqual(addr_param.data_type, "wire [7:0]")
        self.assertEqual(addr_param.default_value, "8'hFF")
        
        # Check ports
        self.assertEqual(len(module.ports), 4)
        clk_port = next(p for p in module.ports if p.name == "clk")
        self.assertIsInstance(clk_port, VerilogPort)
        self.assertEqual(clk_port.mode, "input")
        
        data_port = next(p for p in module.ports if p.name == "data")
        self.assertIsInstance(data_port, VerilogPort)
        self.assertEqual(data_port.mode, "output")
        self.assertEqual(data_port.data_type, "reg [WIDTH-1:0]")
        
        # Check submodules
        self.assertEqual(len(module.submodules), 2)
        sub1 = module.submodules[0]
        self.assertEqual(sub1.module_type, "sub_module")
        self.assertEqual(sub1.instance_name, "sub1")

    def test_udp_module(self):
        """Test parsing the UDP module"""
        # Read and parse UDP module file
        with open(os.path.join(os.path.dirname(__file__), 'udp.v'), 'r') as f:
            udp_text = f.read()
        modules = parse_verilog(udp_text)
        
        # Find the main UDP module
        udp_module = next(m for m in modules if m.name == "udp")
        
        # Test module parameters
        self.assertEqual(len(udp_module.generics), 3)
        params = {p.name: p for p in udp_module.generics}
        
        # Check CHECKSUM_GEN_ENABLE parameter
        self.assertIn('CHECKSUM_GEN_ENABLE', params)
        self.assertEqual(params['CHECKSUM_GEN_ENABLE'].default_value, '1')
        
        # Check CHECKSUM_PAYLOAD_FIFO_DEPTH parameter
        self.assertIn('CHECKSUM_PAYLOAD_FIFO_DEPTH', params)
        self.assertEqual(params['CHECKSUM_PAYLOAD_FIFO_DEPTH'].default_value, '2048')
        
        # Check CHECKSUM_HEADER_FIFO_DEPTH parameter
        self.assertIn('CHECKSUM_HEADER_FIFO_DEPTH', params)
        self.assertEqual(params['CHECKSUM_HEADER_FIFO_DEPTH'].default_value, '8')
        
        # Test ports
        self.assertGreater(len(udp_module.ports), 0)
        ports = {p.name: p for p in udp_module.ports}
        
        # Check clock and reset
        self.assertIn('clk', ports)
        self.assertEqual(ports['clk'].mode, 'input')
        self.assertIn('rst', ports)
        self.assertEqual(ports['rst'].mode, 'input')
        
        # Check some IP frame input ports
        self.assertIn('s_ip_hdr_valid', ports)
        self.assertEqual(ports['s_ip_hdr_valid'].mode, 'input')
        self.assertIn('s_ip_hdr_ready', ports)
        self.assertEqual(ports['s_ip_hdr_ready'].mode, 'output')
        
        # Check some UDP frame output ports
        self.assertIn('m_udp_hdr_valid', ports)
        self.assertEqual(ports['m_udp_hdr_valid'].mode, 'output')
        self.assertIn('m_udp_hdr_ready', ports)
        self.assertEqual(ports['m_udp_hdr_ready'].mode, 'input')
        
        # Check vector ports
        self.assertIn('s_ip_eth_dest_mac', ports)
        self.assertEqual(ports['s_ip_eth_dest_mac'].mode, 'input')
        self.assertEqual(ports['s_ip_eth_dest_mac'].data_type, 'wire [47:0]')
        
        # Check status signals
        self.assertIn('rx_busy', ports)
        self.assertEqual(ports['rx_busy'].mode, 'output')
        self.assertIn('tx_busy', ports)
        self.assertEqual(ports['tx_busy'].mode, 'output')
        
        # Should have three submodules: udp_ip_rx, udp_ip_tx, udp_checksum_gen
        self.assertEqual(len(udp_module.submodules), 3, 
            f"Expected 3 submodules but found {len(udp_module.submodules)}")
        
        # Check udp_ip_rx submodule
        try:
            udp_ip_rx = next(s for s in udp_module.submodules if s.module_type == 'udp_ip_rx')
            self.assertEqual(udp_ip_rx.instance_name, 'udp_ip_rx_inst')
        except StopIteration:
            print("\nERROR: Could not find udp_ip_rx submodule")
            raise

        # Check udp_ip_tx submodule
        try:
            udp_ip_tx = next(s for s in udp_module.submodules if s.module_type == 'udp_ip_tx')
            self.assertEqual(udp_ip_tx.instance_name, 'udp_ip_tx_inst')
        except StopIteration:
            print("\nERROR: Could not find udp_ip_tx submodule")
            raise

        # Check udp_checksum_gen submodule (if CHECKSUM_GEN_ENABLE is 1)
        try:
            udp_checksum_gen = next(s for s in udp_module.submodules if s.module_type == 'udp_checksum_gen')
            self.assertEqual(udp_checksum_gen.instance_name, 'udp_checksum_gen_inst')
        except StopIteration:
            print("\nERROR: Could not find udp_checksum_gen submodule")
            raise


if __name__ == '__main__':
    unittest.main() 