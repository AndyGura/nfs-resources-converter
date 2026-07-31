class DLLNode:
    __slots__ = ("data", "next", "prev")

    def __init__(self, data):
        self.data = data
        self.next = None
        self.prev = None


class DoublyLinkedList:

    @classmethod
    def from_iterable(cls, iterable):
        dll = cls()
        it = iter(iterable)
        try:
            dll.head = prev = DLLNode(next(it))
        except StopIteration:
            return dll
        for item in it:
            new_node = DLLNode(item)
            new_node.prev = prev
            prev.next = new_node
            prev = new_node
        dll.tail = prev
        return dll

    @classmethod
    def from_list(cls, list):
        dll = cls()
        list_len = len(list)
        if list_len == 0:
            return dll
        dll.head = prev = DLLNode(list[0])
        for i in range(1, list_len):
            new_node = DLLNode(list[i])
            new_node.prev = prev
            prev.next = new_node
            prev = new_node
        dll.tail = prev
        return dll

    def __init__(self):
        self.head = None
        self.tail = None

    def prepend(self, data):
        new_node = DLLNode(data)
        if not self.head:
            self.head = new_node
            self.tail = new_node
            return
        self.head.prev = new_node
        new_node.next = self.head
        self.head = new_node

    def append(self, data):
        new_node = DLLNode(data)
        if not self.head:
            self.head = new_node
            self.tail = new_node
            return
        self.tail.next = new_node
        new_node.prev = self.tail
        self.tail = new_node

    def insert(self, data, prev_node, next_node):
        new_node = DLLNode(data)

        if prev_node is not None:
            prev_node.next = new_node
            new_node.prev = prev_node
        else:
            self.head = new_node

        if next_node is not None:
            next_node.prev = new_node
            new_node.next = next_node
        else:
            self.tail = new_node

    def nodes(self):
        item = self.head
        while item is not None:
            yield item
            item = item.next

    def nodes_rev(self):
        item = self.tail
        while item is not None:
            yield item
            item = item.prev

    def items(self):
        for item in self.nodes():
            yield item.data

    def items_rev(self):
        for item in self.nodes_rev():
            yield item.data
